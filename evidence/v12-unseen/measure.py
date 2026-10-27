"""Run a frozen unseen prompt set (default v12) once each through the guarded CPU chat path (baby_boon.chat.complete + guarded),
logging every attempt. Needs scripts/serve.ps1 -Model <model> on --url."""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from baby_boon.chat import GUARD_TRIES, complete
from baby_boon.common import SYSTEM
from baby_boon.cues import CUE_INSTRUCTION
from baby_boon.guard import asks_surroundings, guarded

HERE = pathlib.Path(__file__).parent
p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:11438")
p.add_argument("--label", required=True)
p.add_argument("--dir", type=pathlib.Path, default=HERE, help="folder with prompts.jsonl; results go there too")
a = p.parse_args()

rows = []
for prompt in map(json.loads, open(a.dir / "prompts.jsonl", encoding="utf-8")):
    messages = [{"role": "system", "content": SYSTEM + CUE_INSTRUCTION}, {"role": "user", "content": prompt["text"]}]
    attempts = []

    def generate(attempt):
        attempts.append(complete(a.url, messages, attempt))
        return attempts[-1]

    reply = guarded(generate, GUARD_TRIES, prompt["text"])
    rows.append({**prompt, "routed": asks_surroundings(prompt["text"]), "final": reply["text"],
                 "fallback": bool(reply.get("guard_fallback")), "attempts": [t["text"] for t in attempts],
                 "cue_valid": reply["cue_valid"]})
    print(prompt["id"], len(attempts), "FALLBACK" if rows[-1]["fallback"] else "ok", flush=True)

(a.dir / f"results-{a.label}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"fallbacks {sum(r['fallback'] for r in rows)}/{len(rows)}; attempts {sum(len(r['attempts']) for r in rows)}; "
      f"routed {sum(r['routed'] for r in rows)}")
