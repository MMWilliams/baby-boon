"""Admit a reviewed teacher draft: drop every reply the review rejected and write the rest as a training corpus."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baby_boon.common import digest
from baby_boon.data import audit, read_examples, write_corpus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", default="data/teacher-v1")
    ap.add_argument("--review", default="evidence/teacher-v1-review.json")
    ap.add_argument("--out", default="data/teacher-v1-admitted")
    a = ap.parse_args()
    draft, review_path, out = ROOT / a.draft, ROOT / a.review, ROOT / a.out
    if (out / "manifest.json").exists(): raise FileExistsError("Refusing to replace an admitted corpus")
    audit(draft)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    # The review covers exact file contents; a regenerated draft needs a new review.
    for name, meta in review["corpus_files"].items():
        if digest(draft / name) != meta["sha256"]: raise ValueError(f"{name} changed since review")

    examples = read_examples(draft)
    if len(examples) != review["reviewed_replies"]: raise ValueError("Review does not cover every draft reply")
    rejected = {x["id"] for x in review["rejected"]}
    if unknown := rejected - examples.keys(): raise ValueError(f"Rejected ids not in draft: {sorted(unknown)}")

    out.mkdir(parents=True, exist_ok=True)
    draft_manifest = json.loads((draft / "manifest.json").read_text(encoding="utf-8"))
    del draft_manifest["files"]
    write_corpus(out, [ex for ex_id, ex in examples.items() if ex_id not in rejected], {**draft_manifest,
        "admission": f"Admitted for local training after development review ({review['reviewer']}); "
                     f"{len(rejected)} rejected replies excluded. Not independent human evidence.",
        "draft": a.draft, "draft_manifest_sha256": digest(draft / "manifest.json"),
        "review": a.review, "review_sha256": digest(review_path), "admitter_sha256": digest(Path(__file__)),
        "excluded_replies": sorted(rejected), "admitted_replies": len(examples) - len(rejected),
        "mixed_kept": [x["id"] for x in review["mixed_kept"]]})


if __name__ == "__main__": main()
