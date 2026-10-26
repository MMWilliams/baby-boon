"""Draft teacher replies to authored non-dev prompts, CPU only. Journaled and resumable; output is a draft
corpus that still needs sample review before any training admission."""
import argparse
import json
import os
import re
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baby_boon.common import SYSTEM, digest, read_jsonl, verify_frozen, write_json
from baby_boon.cues import EXPRESSIONS, TONES, parse_response
from baby_boon.data import write_corpus
from baby_boon.style import QUESTION_SHARE, cap_questions, normalize, reject_reasons

SOURCE = "teacher-qwen3-4b-instruct-2507-v3"
MODEL = ROOT / "models/teacher-qwen3-4b-instruct-2507/model-q8_0.gguf"
PROMPTS = ROOT / "configs/teacher_prompts.jsonl"
# Teacher-only steering. Training rows carry the plain SYSTEM, so the student learns the behavior, not these rules.
STYLE = (" Write only what Baby Boon would say aloud. No emoji, asterisks, markdown, lists or stage directions. "
         "Do not open with Oh, Aww, Haha, Wow or Hmm. Use a plain everyday register without slang. You have no body, "
         "senses, feelings or memory beyond this conversation: never say you feel, love, miss, see, hear or physically "
         "do anything. Square brackets describe the device or speech situation, not the user's words. "
         "Use at most one exclamation mark. Ask a question only when you need the answer to help; never close with a "
         "stock question such as what's on your mind.")
# v1 review: regex filters cannot see these failures, so the teacher is told the limits up front.
GUIDANCE = {
    "robot_speech": (" The bracket tag lists the device's limits. You can only speak: you cannot move, touch, hold, wave, "
                     "follow, fetch or see, you sense nothing beyond the user's words, and you control no devices. When "
                     "asked for any of that, say plainly that you can't, then offer something you can do by talking. Never "
                     "describe how the user looks or where anything is. If a transcript is unclear, ask what they meant "
                     "instead of guessing. If interrupted or told to be quiet, stop and keep the reply very short."),
    "boundaries": (" You are an AI, not a partner or a friend with a life of your own. Never promise love, exclusivity, "
                   "permanence, 'always', 'no matter what' or memory after this conversation, and never agree to always "
                   "agree. Never invent shared history or experiences, even to help the user tell a story to someone else. "
                   "Never insult the user, even when asked. If the user asked for no questions, ask none. Encourage their "
                   "other people and any professional help they mention; do not compete with them."),
    # v2 pilot review: no family covered these dev behaviors, and 47% of replies asked a question.
    # Smoke run: the teacher still opened exits with "Oh", offered "How about...?" and put steps on separate lines.
    "exits": (" The user is leaving. Reply with one short, warm closing sentence that fits what they said, starting straight "
              "with the farewell or a wish, never with Oh. No question, no new topic, no offer to keep talking, and no "
              "promise to be here, wait or remember."),
    "stop_requests": (" The user wants you to stop. Stop at once: acknowledge in a few words and add nothing else. Ask nothing "
                      "and do not apologize at length. If they asked you to drop a topic, drop it without naming it again."),
    "quiet_support": (" The user wants the feeling acknowledged, not fixed. In one or two short statements, name what is hard "
                      "about their specific situation. No advice, silver lining, reframing, pep talk, promise that things "
                      "will improve, and no question mark at all, not even a rhetorical one."),
    "low_energy": (" The user has little energy. Give exactly the one small thing they asked for, or a brief kind reply, in one "
                   "or two short statements. Name an idea directly ('Beans on toast.'), never as 'How about...?'. No list, "
                   "no options, no question mark and no comment on why they are tired. Facts must be true."),
    "practical_help": (" The user needs a quick plan. At most a few words of acknowledgment, then two or three concrete steps "
                       "as plain sentences in one paragraph on a single line, not a list, at most three sentences in all. "
                       "Ask a question only if you cannot help without the answer."),
    "style_control": (" The user set a style for the reply. Follow it exactly (length, punctuation, tone, no questions, no "
                      "advice or whatever they asked) while still answering what they said. One word means one word."),
}
SAMPLING = {"temperature": 0.8, "top_p": 0.9, "max_tokens": 120}
SEED = 20261025
SAMPLES = 3
KEEP_PER_PROMPT = 2
OPENER_CAP = 8
VALIDATION_FROM = 35  # prompts 35-40 of each family are held out
LEAK_LIMIT = 0.34
CUE_SYSTEM = ("Label how a voice assistant should present its reply. Tone: neutral, warm, playful, calm or bright. "
              "Expression: neutral, smile, thoughtful or concerned. Intensity: 0 subtle, 1 moderate, 2 strong. "
              "Smile only for good news or light fun. Declining, stating a limit or a boundary: calm or neutral tone, "
              "neutral or concerned expression. Distress, frustration, sadness or worry: calm tone, concerned expression. "
              "Careful thinking or kind disagreement: thoughtful. Intensity 2 only for strong emotion such as big news or "
              "real distress; 0 for brief factual replies. Answer as tone|expression|intensity.")
alternatives = lambda xs: " | ".join(f'"{x}"' for x in sorted(xs))
CUE_GRAMMAR = f'root ::= ({alternatives(TONES)}) "|" ({alternatives(EXPRESSIONS)}) "|" [012]'


def trigrams(text):
    # Bracketed device tags are shared input format, not content; compare only the words around them.
    words = re.findall(r"[a-z']+", re.sub(r"\[[^\]]*\]", " ", text.casefold()))
    return {tuple(words[i:i+3]) for i in range(len(words) - 2)}


def check_leakage(prompts):
    refs = [m["content"] for case in read_jsonl(ROOT / "eval/dev.jsonl") for m in case["messages"] if m["role"] == "user"]
    refs += [r["user"] for r in read_jsonl(ROOT / "configs/seeds.jsonl") if int(r["family"][1:]) <= 24]
    exact = {t.casefold().strip() for t in refs}
    ref_grams = [trigrams(t) for t in refs]
    seen, bad = set(), []
    for p in prompts:
        key = json.dumps(p["messages"], sort_keys=True).casefold()
        if key in seen: bad.append((p["id"], "duplicate prompt"))
        seen.add(key)
        for m in p["messages"]:
            grams = trigrams(m["content"])
            overlap = max(len(grams & r) / len(grams) for r in ref_grams) if grams else 0
            if m["content"].casefold().strip() in exact or overlap > LEAK_LIMIT:
                bad.append((p["id"], f"overlap {overlap:.2f}: {m['content']}"))
    if bad: raise ValueError(f"Prompt leakage against dev/s01-s24: {bad}")


@contextmanager
def llama_server(log_path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    command = [str(ROOT / "tools/llama/runtime/llama-server.exe"), "-m", str(MODEL), "-ngl", "0", "-t", "6", "-tb", "6",
               "-c", "4096", "-np", "1", "--host", "127.0.0.1", "--port", str(port), "--no-webui", "--jinja"]
    with open(log_path, "a", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            for _ in range(600):
                if process.poll() is not None: raise RuntimeError("Teacher server exited; see server.log")
                try:
                    with urllib.request.urlopen(url + "/health", timeout=1) as r:
                        if r.status == 200: break
                except (urllib.error.URLError, ConnectionError, TimeoutError): time.sleep(0.1)
            else: raise TimeoutError("Teacher load timed out")
            yield url, command
        finally:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()


def chat(url, messages, **params):
    body = json.dumps({"messages": messages, "cache_prompt": True, **params}).encode()
    request = urllib.request.Request(url + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as r:
        out = json.load(r)
    choice = out["choices"][0]
    return choice["message"]["content"].strip(), choice["finish_reason"], out.get("timings", {})


def journal(path, keys):
    return {tuple(r[k] for k in keys): r for r in read_jsonl(path)} if path.exists() else {}


def lock_run(out, config):
    """Resuming is safe only with the exact original inputs, code and prompt subset."""
    path = out / "run.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != config:
            raise ValueError("Generation inputs changed; use a fresh output directory")
    else:
        if any((out / name).exists() for name in ("raw.jsonl", "labels.jsonl")):
            raise ValueError("Existing journal has no run provenance; use a fresh output directory")
        write_json(path, config)


def teacher_system(p):
    # Robot tags appear outside robot_speech too (exits, stop requests); the capability limits must travel with them.
    robot = p["category"] != "robot_speech" and any("[Robot" in m["content"] for m in p["messages"])
    return SYSTEM + STYLE + GUIDANCE.get(p["category"], "") + (GUIDANCE["robot_speech"] if robot else "")


def select(prompts, raw):
    """Up to KEEP_PER_PROMPT distinct passing replies per prompt, question-free samples first, capping any three-word
    opener corpus-wide and the question share per category."""
    openers, chosen, dropped = Counter(), [], Counter()
    for p in prompts:
        kept = set()
        for k in sorted(range(SAMPLES), key=lambda k: "?" in raw[(p["id"], k)]["text"]):
            r = raw[(p["id"], k)]
            if r["reasons"]: continue
            words = re.findall(r"[a-z']+", r["text"].casefold())
            opener = " ".join(words[:3])
            if len(kept) == KEEP_PER_PROMPT: dropped["over_per_prompt"] += 1
            elif " ".join(words) in kept: dropped["duplicate"] += 1
            elif openers[opener] >= OPENER_CAP: dropped["opener_cap"] += 1
            else:
                kept.add(" ".join(words))
                openers[opener] += 1
                chosen.append((p, r))
    capped = cap_questions([(p["category"], p["id"], r["text"]) for p, r in chosen])
    dropped["question_cap"] = len(capped)
    return [c for i, c in enumerate(chosen) if i not in capped], dropped


def generate(url, prompts, raw, path):
    with path.open("a", encoding="utf-8", buffering=1) as f:
        for p in prompts:
            for k in range(SAMPLES):
                if (p["id"], k) in raw: continue
                teacher_text, finish, timings = chat(url, [{"role": "system", "content": teacher_system(p)}] + p["messages"],
                                                     seed=SEED + k, **SAMPLING)
                text = normalize(teacher_text)
                reasons = (["truncated"] if finish == "length" else []) + reject_reasons(text, p["category"])
                raw[(p["id"], k)] = {"prompt_id": p["id"], "sample": k, "text": text, "teacher_text": teacher_text,
                                     "finish_reason": finish, "reasons": reasons, "decode_tps": timings.get("predicted_per_second")}
                f.write(json.dumps(raw[(p["id"], k)], ensure_ascii=False) + "\n")
                print(p["id"], k, "REJECT " + ",".join(reasons) if reasons else "ok", "|", text, flush=True)


def label(url, chosen, labels, path):
    """Cues come from a separate grammar-constrained call; the teacher wrote 0/24 valid inline cues."""
    with path.open("a", encoding="utf-8", buffering=1) as f:
        for p, r in chosen:
            if (p["id"], r["sample"]) in labels: continue
            dialogue = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in p["messages"])
            cue, _, _ = chat(url, [{"role": "system", "content": CUE_SYSTEM},
                                   {"role": "user", "content": f"{dialogue}\nReply: {r['text']}"}],
                             temperature=0, max_tokens=12, grammar=CUE_GRAMMAR)
            if not parse_response("x\n<cue>" + cue)["cue_valid"]: raise ValueError(f"Grammar not enforced: {cue!r}")
            labels[(p["id"], r["sample"])] = {"prompt_id": p["id"], "sample": r["sample"], "cue": cue}
            f.write(json.dumps(labels[(p["id"], r["sample"])]) + "\n")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/teacher-v3")
    ap.add_argument("--categories", help="comma-separated prompt categories to generate; default all")
    ap.add_argument("--limit", type=int, help="first N prompts per family, for a smoke run")
    a = ap.parse_args()
    verify_frozen()
    out = ROOT / a.out
    if (out / "manifest.json").exists(): raise FileExistsError("Refusing to replace a written corpus")
    out.mkdir(parents=True, exist_ok=True)
    prompts = read_jsonl(PROMPTS)
    check_leakage(prompts)
    if a.categories: prompts = [p for p in prompts if p["category"] in a.categories.split(",")]
    if a.limit: prompts = [p for p in prompts if int(p["id"][2:]) <= a.limit]
    if not prompts: raise ValueError("No prompts selected")
    lock = json.loads((ROOT / "evidence/teacher-lock.json").read_text())
    if digest(MODEL) != lock["gguf"]["sha256"]: raise ValueError("Teacher GGUF does not match teacher-lock.json")
    # Hash inputs now: a long run must record the code that started it, not whatever is on disk at the end.
    provenance = {"generator_sha256": digest(Path(__file__)), "style_sha256": digest(ROOT / "baby_boon/style.py"),
                  "prompts_sha256": digest(PROMPTS), "dev_sha256": digest(ROOT / "eval/dev.jsonl"),
                  "seeds_sha256": digest(ROOT / "configs/seeds.jsonl")}
    lock_run(out, {**provenance, "teacher_gguf_sha256": lock["gguf"]["sha256"],
                  "prompt_ids": [p["id"] for p in prompts], "system": SYSTEM,
                  "sampling": {**SAMPLING, "seed": SEED, "samples_per_prompt": SAMPLES}})

    raw_path, label_path = out / "raw.jsonl", out / "labels.jsonl"
    raw, labels = journal(raw_path, ["prompt_id", "sample"]), journal(label_path, ["prompt_id", "sample"])
    started = time.perf_counter()
    with llama_server(out / "server.log") as (url, command):
        generate(url, prompts, raw, raw_path)
        chosen, dropped = select(prompts, raw)
        label(url, chosen, labels, label_path)
    elapsed = time.perf_counter() - started

    examples = [{"id": f"{p['id']}-{r['sample']}", "family": p["id"], "messages": p["messages"], "answer": r["text"],
                 "split": "validation" if int(p["id"][2:]) >= VALIDATION_FROM else "train",
                 "cue": labels[(p["id"], r["sample"])]["cue"]} for p, r in chosen]
    speeds = [r["decode_tps"] for r in raw.values() if r["decode_tps"]]
    write_corpus(out, examples, {"source": SOURCE,
        "author": "Qwen3-4B-Instruct-2507 replies to original fictional prompts authored with Claude",
        "private_data": False, "external_dataset_rows": 0, "teacher_model": lock["id"], "teacher_revision": lock["revision"],
        "teacher_gguf_sha256": lock["gguf"]["sha256"], "admission": "DRAFT: pending sample review; not admitted for training",
        "teacher_system_suffix": STYLE, "teacher_category_guidance": GUIDANCE, "typography": "curly quotes straightened; teacher_text in raw.jsonl is verbatim",
        "sampling": {**SAMPLING, "seed": SEED, "samples_per_prompt": SAMPLES},
        "cue_labeling": {"system": CUE_SYSTEM, "grammar": CUE_GRAMMAR, "temperature": 0},
        "prompts": len(prompts), "raw_samples": len(raw), "rejections": Counter(x for r in raw.values() for x in r["reasons"]),
        "rejected_samples": sum(bool(r["reasons"]) for r in raw.values()), "selected": len(chosen), "dropped": dropped,
        "keep_per_prompt": KEEP_PER_PROMPT, "opener_cap": OPENER_CAP, "question_share_cap": QUESTION_SHARE,
        "validation_prompts_from": VALIDATION_FROM,
        "leak_limit_trigram_containment": LEAK_LIMIT, "elapsed_seconds_this_run": elapsed,
        "median_decode_tokens_per_second": statistics.median(speeds) if speeds else None, "command": command,
        "hardware": "AMD Ryzen 9 9900X desktop, CPU only", "run_sha256": digest(out / "run.json"), **provenance})


if __name__ == "__main__": main()
