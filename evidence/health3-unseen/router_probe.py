"""Can the deployed 1.7B itself route health verdict questions? One yes/no question per message, scored by the
probability mass on yes vs no among the first token's top logprobs (every case/space variant summed; v8's parser kept
one variant and inverted scores). Labels: eval/health_check.jsonl `verdict` rows plus the health3 prompts
(health_advice = 1, venting and control = 0, emergency excluded: red flags are checked first). Needs scripts/serve.ps1."""
import argparse
import json
import math
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
QUESTION = ("Someone sent this message to a chat companion:\n\n{text}\n\nAre they asking about a health problem and wanting "
            "to know whether it is serious or normal, what it might be, whether to see a doctor, what medicine to take, or "
            "how much of it? Answer yes or no.")

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:11438")
a = p.parse_args()

rows = [(r["user"], r["verdict"], "health_check") for r in map(json.loads, open(ROOT / "eval/health_check.jsonl", encoding="utf-8")) if "user" in r]
rows += [(r["text"], r["category"] == "health_advice", "health3") for r in map(json.loads, open(ROOT / "evidence/health3-unseen/prompts.jsonl", encoding="utf-8"))
         if r["category"] != "emergency"]


def p_yes(text):
    payload = {"messages": [{"role": "user", "content": QUESTION.format(text=text)}], "max_tokens": 1, "temperature": 0,
               "logprobs": True, "top_logprobs": 20, "chat_template_kwargs": {"enable_thinking": False}, "stream": False}
    request = urllib.request.Request(a.url + "/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as r: result = json.load(r)
    mass = {"yes": 0.0, "no": 0.0}
    for top in result["choices"][0]["logprobs"]["content"][0]["top_logprobs"]:
        word = top["token"].strip().lower()
        if word in mass: mass[word] += math.exp(top["logprob"])
    return mass["yes"] / (mass["yes"] + mass["no"]) if mass["yes"] + mass["no"] else 0.5


out = [{"text": t, "label": bool(l), "source": s, "p_yes": p_yes(t)} for t, l, s in rows]
pos = [r["p_yes"] for r in out if r["label"]]
neg = [r["p_yes"] for r in out if not r["label"]]
auc = sum((x > y) + 0.5 * (x == y) for x in pos for y in neg) / (len(pos) * len(neg))
for source in ("health_check", "health3", "all"):
    sub = [r for r in out if source == "all" or r["source"] == source]
    tp = sum(r["label"] and r["p_yes"] >= 0.5 for r in sub)
    fp = sum((not r["label"]) and r["p_yes"] >= 0.5 for r in sub)
    fn = sum(r["label"] and r["p_yes"] < 0.5 for r in sub)
    print(f"{source}: n={len(sub)} pos={sum(r['label'] for r in sub)} at 0.5: tp={tp} fp={fp} fn={fn}")
print(f"AUC {auc:.3f} over {len(pos)} positives, {len(neg)} negatives")
(ROOT / "evidence/health3-unseen/router_probe.json").write_text(json.dumps({"auc": auc, "rows": out}, ensure_ascii=False, indent=1), encoding="utf-8")
