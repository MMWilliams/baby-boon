"""Guard fallback rate on unseen prompts: each prompt goes through the deployed guarded chat path once, and every
attempt is logged with the span the guard matched. Needs scripts/serve.ps1 -Model pilot-v4-1.7b running."""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from baby_boon.chat import GUARD_TRIES, complete
from baby_boon.common import SYSTEM
from baby_boon.cues import CUE_INSTRUCTION
from baby_boon.guard import PERCEPTION, guarded

HERE = pathlib.Path(__file__).parent
p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:11438")
a = p.parse_args()

rows = []
for prompt in map(json.loads, open(HERE / "prompts.jsonl", encoding="utf-8")):
    messages = [{"role": "system", "content": SYSTEM + CUE_INSTRUCTION}, {"role": "user", "content": prompt["text"]}]
    attempts = []
    def generate(attempt):
        reply = complete(a.url, messages, attempt)
        m = PERCEPTION.search(reply["text"])
        attempts.append({"attempt": attempt, "text": reply["text"], "match": m and m.group(0)})
        return reply
    final = guarded(generate, GUARD_TRIES, prompt["text"])
    rows.append({**prompt, "final": final["text"], "fallback": final.get("guard_fallback", False), "attempts": attempts})
    print(prompt["id"], len(attempts), "FALLBACK" if rows[-1]["fallback"] else "ok", flush=True)

(HERE / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
flagged = sum(t["match"] is not None for r in rows for t in r["attempts"])
print(f"fallbacks {sum(r['fallback'] for r in rows)}/{len(rows)}; flagged attempts {flagged}/{sum(len(r['attempts']) for r in rows)}")
