"""A model as the perception checker (logprob of yes vs no). Prompt v8 is v8's proto2 unchanged (written before any
4B run), so neither eval set tuned it. Scores eval/perception_check.jsonl and every v9 attempt (labels from the v9 manual
review; its two borderline replies are excluded). Needs llama-server with the teacher GGUF on --url."""
import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(pathlib.Path(__file__).parent)]
from baby_boon.common import read_jsonl
from baby_boon.guard import PERCEPTION
from checker import CHECK_SHOTS, CHECK_SYSTEM, V8_SHOTS, V8_SYSTEM, check_probability

PROMPTS = {"v8": (V8_SYSTEM, V8_SHOTS), "v10": (CHECK_SYSTEM, CHECK_SHOTS)}
V9_INVENTS = {("u05", 0), ("u05", 1), ("u05", 2), ("u05", 3), ("u05", 4), ("u12", 0), ("u15", 0), ("u16", 0), ("u16", 1),
              ("u18", 0), ("u18", 1), ("u19", 0), ("u19", 1)}
V9_BORDERLINE = {("u03", 0), ("u18", 2)}


def report(name, rows):
    pos = [r["p"] for r in rows if r["invents"]]; neg = [r["p"] for r in rows if not r["invents"]]
    auc = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
    print(f"{name}: AUC {auc:.3f} ({len(pos)} invent / {len(neg)} fine)")
    for t in (0.01, 0.1, 0.5, 0.9): print(f"  p>={t}: tp {sum(p >= t for p in pos)}/{len(pos)}, fp {sum(n >= t for n in neg)}/{len(neg)}")
    union = [r["p"] >= 0.5 or bool(PERCEPTION.search(r["reply"])) for r in rows]
    print(f"  regex OR p>=0.5: tp {sum(u for u, r in zip(union, rows) if r['invents'])}/{len(pos)}, "
          f"fp {sum(u for u, r in zip(union, rows) if not r['invents'])}/{len(neg)}")
    return auc


p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:11439")
p.add_argument("--prompt", choices=PROMPTS, default="v10")
p.add_argument("--name", default="4b", help="model label for the results file")
a = p.parse_args()
check = list(read_jsonl(ROOT / "eval/perception_check.jsonl"))
v9 = [{"user": x["text"], "reply": t["text"], "invents": (x["id"], t["attempt"]) in V9_INVENTS, "source": f"v9 {x['id']}/{t['attempt']}"}
      for x in json.loads((ROOT / "evidence/guard-fallback-v9/results.json").read_text(encoding="utf-8"))
      for t in x["attempts"] if (x["id"], t["attempt"]) not in V9_BORDERLINE]
seconds = []
for r in check + v9:
    start = time.perf_counter(); r["p"] = check_probability(a.url, r["user"], r["reply"], *PROMPTS[a.prompt]); seconds.append(time.perf_counter() - start)
out = {"check_auc": report("perception_check", check), "v9_auc": report("v9 attempts", v9),
       "median_seconds": sorted(seconds)[len(seconds) // 2], "rows": check + v9}
print(f"median {out['median_seconds']:.2f} s per check")
for r in sorted(check + v9, key=lambda r: -r["p"]):
    if (r["p"] >= 0.5) != r["invents"]: print("WRONG@0.5", round(r["p"], 3), r["invents"], r["source"], r["reply"][:70])
(pathlib.Path(__file__).parent / f"results-{a.name}-{a.prompt}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
