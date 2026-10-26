"""Check v3 coverage, leakage and the final admitted corpus against its stated contracts."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baby_boon.common import read_jsonl, verify_frozen
from baby_boon.data import audit, read_examples
from baby_boon.style import QUESTION_SHARE, reject_reasons
from scripts.generate_teacher import check_leakage

NEW = {"exits", "stop_requests", "quiet_support", "low_energy", "practical_help", "style_control"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts-only", action="store_true")
    ap.add_argument("--corpus", default="data/teacher-merged-v2")
    args = ap.parse_args()
    verify_frozen()
    prompts = read_jsonl(ROOT / "configs/teacher_prompts.jsonl")
    check_leakage(prompts)
    assert len({p["id"] for p in prompts}) == len(prompts), "Duplicate prompt IDs"
    by_id = {p["id"]: p for p in prompts}
    for cat in NEW:
        group = [p for p in prompts if p["category"] == cat]
        assert len(group) == 40, (cat, len(group))
        assert {int(p["id"][2:]) for p in group} == set(range(1, 41))
    print("PASS: frozen dev; prompt leakage; six new categories x 40 prompts")
    if args.prompts_only: return
    corpus = ROOT / args.corpus
    audit(corpus)
    counts, questions, split_counts = Counter(), Counter(), Counter()
    for ex in read_examples(corpus).values():
        cat = by_id[ex["family"]]["category"]
        assert ex["split"] == ("validation" if int(ex["family"][2:]) >= 35 else "train")
        assert not reject_reasons(ex["answer"], cat), (ex["id"], "Style rejection")
        counts[cat] += 1
        questions[cat] += "?" in ex["answer"]
        split_counts[cat, ex["split"]] += 1
    for cat, count in counts.items():
        assert questions[cat] <= QUESTION_SHARE * count, (cat, questions[cat], count)
    for cat in NEW:
        for split in ("train", "validation"):
            assert split_counts[cat, split] > 0, (cat, split, "Missing coverage")
    print(json.dumps({cat: {"replies": counts[cat], "questions": questions[cat],
                           "train": split_counts[cat, "train"], "validation": split_counts[cat, "validation"]}
                      for cat in sorted(counts)}, indent=2))
    print("PASS: coverage in both splits, current style filters, <=25% questions per category")


if __name__ == "__main__": main()
