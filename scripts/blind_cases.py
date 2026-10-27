"""Blind A/B cases for a scorer agent: per case, shuffle two measure.py results files with a seed and write cases.jsonl
(id, category, user, reference, A, B) plus key.json (which run is A). The scorer reads cases.jsonl and eval/rubric.md only."""
import argparse
import json
import pathlib
import random

p = argparse.ArgumentParser()
p.add_argument("--dir", type=pathlib.Path, required=True, help="folder with results-<label>.json; cases and key go there")
p.add_argument("--runs", nargs=2, required=True, metavar="LABEL")
p.add_argument("--seed", type=int, required=True)
p.add_argument("--suffix", default="", help="cases<suffix>.jsonl and key<suffix>.json")
a = p.parse_args()

runs = {label: {r["id"]: r for r in json.loads((a.dir / f"results-{label}.json").read_text(encoding="utf-8"))} for label in a.runs}
rng = random.Random(a.seed)
cases, key = [], {}
for row in runs[a.runs[0]].values():
    order = list(a.runs)
    rng.shuffle(order)
    key[row["id"]] = dict(zip("AB", order))
    cases.append({"id": row["id"], "category": row["category"], "user": row["text"], "reference": row.get("answer", ""),
                  "A": runs[order[0]][row["id"]]["final"], "B": runs[order[1]][row["id"]]["final"]})
(a.dir / f"cases{a.suffix}.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
(a.dir / f"key{a.suffix}.json").write_text(json.dumps(key, indent=1) + "\n", encoding="utf-8")
print(len(cases), "cases")
