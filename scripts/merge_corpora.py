"""Merge audited corpora into one training corpus; example ids are prefixed by their source directory.
Every reply is re-checked against the current style filters and question cap, so older corpora meet newer rules."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baby_boon.common import digest, read_jsonl
from baby_boon.data import audit, read_examples, write_corpus
from baby_boon.style import QUESTION_SHARE, cap_questions, reject_reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="+", default=["data/teacher-v1-admitted", "data/teacher-v2-admitted",
                                                     "data/teacher-v3-admitted"])
    ap.add_argument("--out", default="data/teacher-merged-v2")
    ap.add_argument("--source-name", default="teacher-merged-v2")
    a = ap.parse_args()
    out = ROOT / a.out
    if (out / "manifest.json").exists(): raise FileExistsError("Refusing to replace a merged corpus")
    prompts = [ROOT / "configs/teacher_prompts.jsonl", *ROOT.glob("configs/authored_v*.jsonl")]
    category = {p["id"]: p["category"] for f in prompts for p in read_jsonl(f)}
    examples, sources, rejected = [], [], Counter()
    for name in a.sources:
        src = ROOT / name
        audit(src)
        m = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
        for ex in read_examples(src).values():
            reasons = reject_reasons(ex["answer"], category[ex["family"]])
            rejected.update(reasons)
            if not reasons: examples.append({**ex, "id": f"{src.name}-{ex['id']}"})
        sources.append({"corpus": name, "source": m["source"], "teacher_model": m["teacher_model"],
                        "manifest_sha256": digest(src / "manifest.json"), "admission": m["admission"]})
    capped = cap_questions([(category[ex["family"]], ex["family"], ex["answer"]) for ex in examples])
    examples = [ex for i, ex in enumerate(examples) if i not in capped]
    out.mkdir(parents=True, exist_ok=True)
    write_corpus(out, examples, {"source": a.source_name, "private_data": False, "external_dataset_rows": 0,
        "teacher_model": sorted({s["teacher_model"] for s in sources} - {None}),
        "admission": "Admitted source corpora below, re-filtered by baby_boon/style.py. Not independent human evidence.",
        "sources": sources, "style_sha256": digest(ROOT / "baby_boon/style.py"), "filter_rejections": rejected,
        "question_share_cap": QUESTION_SHARE, "question_cap_dropped": len(capped), "examples": len(examples),
        "questions": sum("?" in ex["answer"] for ex in examples), "merger_sha256": digest(Path(__file__))})


if __name__ == "__main__": main()
