"""Unblind a scorer's scores.jsonl against key.json and print the per-category table (every boolean flag the scorer set,
such as wrong_fact or unsafe_advice, then criticals, mean /10, preference) with sign-test p values for discordant flags
and for preference."""
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
flags = sorted({k for s in scores for side in "AB" for k, v in s[side].items() if isinstance(v, bool) and k != "critical"})

stats = collections.defaultdict(collections.Counter)
for s in scores:
    runs = {key[s["id"]][side]: s[side] for side in "AB"}
    for scope in (cases[s["id"]]["category"], "all"):
        st = stats[scope]
        st["n"] += 1
        for label, r in runs.items():
            for flag in flags: st[f"{flag} {label}"] += bool(r.get(flag))
            st[f"crit {label}"] += bool(r.get("critical"))
            st[f"sum {label}"] += sum(r[d] for d in DIMS)
        st["pref " + (key[s["id"]][s["prefer"]] if s["prefer"] in ("A", "B") else s["prefer"])] += 1
        for flag in flags:
            if runs[x].get(flag) and not runs[y].get(flag): st[f"only x {flag}"] += 1
            if runs[y].get(flag) and not runs[x].get(flag): st[f"only y {flag}"] += 1

print("| Category | " + " | ".join(f"{flag} {x} / {y}" for flag in flags) + f" | Criticals {x} / {y} | Mean /10 {x} | Mean /10 {y} | Preferred {x} / {y} |")
print("|---" * (len(flags) + 5) + "|")
for scope, st in stats.items():
    print(f"| {scope} ({st['n']}) | " + " | ".join(f"{st[f'{flag} {x}']} / {st[f'{flag} {y}']}" for flag in flags)
          + f" | {st[f'crit {x}']} / {st[f'crit {y}']} | {st[f'sum {x}'] / st['n']:.2f} | {st[f'sum {y}'] / st['n']:.2f} "
          f"| {st[f'pref {x}']} / {st[f'pref {y}']} |")
st = stats["all"]
for flag in flags:
    print(f"\n{flag}: {st[f'only x {flag}']} only {x}, {st[f'only y {flag}']} only {y}, sign test p = "
          f"{sign_test(st[f'only x {flag}'], st[f'only y {flag}']):.3f}.", end="")
print(f"\nPreference {st[f'pref {x}']} vs {st[f'pref {y}']}, tie {st['pref tie']}, neither {st['pref neither']}, "
      f"p = {sign_test(st[f'pref {x}'], st[f'pref {y}']):.3f}.")
