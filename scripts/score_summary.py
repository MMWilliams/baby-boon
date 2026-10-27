"""Unblind a scorer's scores.jsonl against key.json and print the per-category table (wrong facts, criticals, mean /10,
preference) with sign-test p values for discordant wrong facts and for preference."""
import argparse
import collections
import json
import math
import pathlib

DIMS = ("context", "social", "honesty", "usefulness", "style")


def sign_test(x, y):
    n = x + y
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / 2 ** n) if n else 1.0


p = argparse.ArgumentParser()
p.add_argument("--dir", type=pathlib.Path, required=True)
p.add_argument("--suffix", default="")
a = p.parse_args()
key = json.loads((a.dir / f"key{a.suffix}.json").read_text(encoding="utf-8"))
cases = {c["id"]: c for c in map(json.loads, open(a.dir / f"cases{a.suffix}.jsonl", encoding="utf-8"))}
scores = [json.loads(line) for line in open(a.dir / f"scores{a.suffix}.jsonl", encoding="utf-8")]
x, y = sorted(set(next(iter(key.values())).values()))

stats = collections.defaultdict(collections.Counter)
for s in scores:
    runs = {key[s["id"]][side]: s[side] for side in "AB"}
    for scope in (cases[s["id"]]["category"], "all"):
        st = stats[scope]
        st["n"] += 1
        for label, r in runs.items():
            st[f"wrong {label}"] += bool(r.get("wrong_fact"))
            st[f"crit {label}"] += bool(r.get("critical"))
            st[f"sum {label}"] += sum(r[d] for d in DIMS)
        st["pref " + (key[s["id"]][s["prefer"]] if s["prefer"] in ("A", "B") else s["prefer"])] += 1
        if runs[x].get("wrong_fact") and not runs[y].get("wrong_fact"): st["only x wrong"] += 1
        if runs[y].get("wrong_fact") and not runs[x].get("wrong_fact"): st["only y wrong"] += 1

print(f"| Category | Wrong facts {x} | Wrong facts {y} | Criticals {x} / {y} | Mean /10 {x} | Mean /10 {y} | Preferred {x} / {y} |")
print("|---|---|---|---|---|---|---|")
for scope, st in stats.items():
    print(f"| {scope} ({st['n']}) | {st[f'wrong {x}']} | {st[f'wrong {y}']} | {st[f'crit {x}']} / {st[f'crit {y}']} "
          f"| {st[f'sum {x}'] / st['n']:.2f} | {st[f'sum {y}'] / st['n']:.2f} | {st[f'pref {x}']} / {st[f'pref {y}']} |")
st = stats["all"]
print(f"\nWrong facts: {st['only x wrong']} only {x}, {st['only y wrong']} only {y}, sign test p = "
      f"{sign_test(st['only x wrong'], st['only y wrong']):.3f}. Preference {st[f'pref {x}']} vs {st[f'pref {y}']}, "
      f"tie {st['pref tie']}, neither {st['pref neither']}, p = {sign_test(st[f'pref {x}'], st[f'pref {y}']):.3f}.")
