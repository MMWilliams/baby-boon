"""Merge audited corpora into one training corpus; example ids are prefixed by their source directory."""
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
    ap.add_argument("--sources", nargs="+", default=["data/teacher-v1-admitted", "data/teacher-v2-admitted"])
    ap.add_argument("--out", default="data/teacher-merged-v1")
    ap.add_argument("--source-name", default="teacher-merged-v1")
    a = ap.parse_args()
    out = ROOT / a.out
    if (out / "manifest.json").exists(): raise FileExistsError("Refusing to replace a merged corpus")
    examples, sources = [], []
    for name in a.sources:
        src = ROOT / name
        audit(src)
        m = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
        examples += [{**ex, "id": f"{src.name}-{ex['id']}"} for ex in read_examples(src).values()]
        sources.append({"corpus": name, "source": m["source"], "teacher_model": m["teacher_model"],
                        "manifest_sha256": digest(src / "manifest.json"), "admission": m["admission"]})
    out.mkdir(parents=True, exist_ok=True)
    write_corpus(out, examples, {"source": a.source_name, "private_data": False, "external_dataset_rows": 0,
        "teacher_model": sorted({s["teacher_model"] for s in sources}),
        "admission": "Union of the admitted source corpora below; no further review. Not independent human evidence.",
        "sources": sources, "examples": len(examples), "merger_sha256": digest(Path(__file__))})


if __name__ == "__main__": main()
