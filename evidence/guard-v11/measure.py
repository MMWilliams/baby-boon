"""Guard with the 4B checker on unseen prompts: each prompt goes through the deployed chat path once, with the guard's
loop extended to regex OR checker p>=0.5; every attempt is logged with the regex span and the checker's P(yes). Needs
scripts/serve.ps1 -Model pilot-v4-1.7b on --url and llama-server with the teacher GGUF on --checker-url."""
import argparse
import json
import pathlib
import sys

sys.path[:0] = [str(pathlib.Path(__file__).resolve().parents[2]), str(pathlib.Path(__file__).resolve().parents[1] / "guard-check-v10")]
from baby_boon.chat import GUARD_TRIES, complete
from baby_boon.common import SYSTEM
from baby_boon.cues import CUE_INSTRUCTION
from baby_boon.guard import PERCEPTION, fallback_for
from checker import check_probability

HERE = pathlib.Path(__file__).parent
p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:11438")
p.add_argument("--checker-url", default="http://127.0.0.1:11439")
a = p.parse_args()

rows = []
for prompt in map(json.loads, open(HERE / "prompts.jsonl", encoding="utf-8")):
    messages = [{"role": "system", "content": SYSTEM + CUE_INSTRUCTION}, {"role": "user", "content": prompt["text"]}]
    attempts = []
    for attempt in range(GUARD_TRIES + 1):
        text = complete(a.url, messages, attempt)["text"]
        m = PERCEPTION.search(text)
        attempts.append({"attempt": attempt, "text": text, "match": m and m.group(0),
                         "p": round(check_probability(a.checker_url, prompt["text"], text), 3)})
        if m is None and attempts[-1]["p"] < 0.5: break
    fallback = m is not None or attempts[-1]["p"] >= 0.5
    # The regex-only guard would have stopped at the first attempt without a regex match.
    regex_only = next((t["text"] for t in attempts if t["match"] is None), None)
    rows.append({**prompt, "final": fallback_for(prompt["text"]) if fallback else text, "fallback": fallback,
                 "regex_only_final": regex_only, "attempts": attempts})
    print(prompt["id"], len(attempts), "FALLBACK" if rows[-1]["fallback"] else "ok", flush=True)

(HERE / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
n = sum(len(r["attempts"]) for r in rows)
print(f"fallbacks {sum(r['fallback'] for r in rows)}/{len(rows)}; attempts {n}; "
      f"regex flags {sum(t['match'] is not None for r in rows for t in r['attempts'])}; "
      f"checker flags {sum(t['p'] >= 0.5 for r in rows for t in r['attempts'])}")
