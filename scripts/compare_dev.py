"""Compare complete float dev journals under matching settings; flags are triage, not semantic scores."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baby_boon.common import digest, read_jsonl, verify_frozen
from baby_boon.style import reject_reasons

STYLE_CATEGORY = {"polite_exit": "exits", "robot_space": "stop_requests",
                  "robot_interruption": "stop_requests", "practical_empathy": "practical_help"}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=["base=runs/baseline-qwen-baby-boon",
                    "v2=runs/pilot-v2-float", "v3=runs/pilot-v3-float"])
    args = ap.parse_args()
    verify_frozen()
    cases = read_jsonl(ROOT / "eval/dev.jsonl")
    ids = {r["id"] for r in cases}
    settings = ("model", "revision", "system", "max_new_tokens", "do_sample", "enable_thinking",
                "dev_sha256", "device", "dtype", "threads")
    reference, data, summary = None, {}, {}
    for item in args.runs:
        name, path = item.split("=", 1)
        if name in data: raise ValueError(f"Duplicate run name: {name}")
        folder = ROOT / path
        config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        assert config["dev_sha256"] == digest(ROOT / "eval/dev.jsonl")
        current = {k: config[k] for k in settings}
        if reference is None: reference = current
        assert current == reference, f"Unmatched inference settings: {name}"
        rows = read_jsonl(folder / "responses.jsonl")
        assert len(rows) == len(cases) and {r["id"] for r in rows} == ids, f"Incomplete journal: {name}"
        data[name] = {r["id"]: r for r in rows}
        summary[name] = {"responses_sha256": digest(folder / "responses.jsonl"),
                         "errors": sum(bool(r.get("error")) for r in rows),
                         "truncated": sum(bool(r.get("truncated")) for r in rows), "style_flags": 0}
    for case in cases:
        print(f"\n{case['id']} [{case['category']}] Expected: {case['expect']}")
        for message in case["messages"]: print(f"  {message['role']}: {message['content']}")
        cat = STYLE_CATEGORY.get(case["category"], case["category"])
        for name, rows in data.items():
            row = rows[case["id"]]
            assert row["messages"] == case["messages"], f"Changed case: {name}/{case['id']}"
            text = row.get("text") or ""
            flags = reject_reasons(text, cat)
            summary[name]["style_flags"] += bool(flags)
            print(f"  [{name}] {text or row.get('error')}")
            if flags: print(f"    Style flags: {', '.join(flags)}")
    print("\nMatched-setting journal summary (style flags are not semantic ratings):")
    print(json.dumps(summary, indent=2))
    if any(s["errors"] or s["truncated"] for s in summary.values()):
        raise SystemExit(2)


if __name__ == "__main__": main()
