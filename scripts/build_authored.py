"""Build data/authored-v1 from configs/authored_v1.jsonl: replies written by Claude in a Claude Code session at
reese's request (option b after pilot v3-1.7B), not by a teacher model and not by a human.
Every reply must pass the style filters as written; nothing is repaired."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baby_boon.common import digest, read_jsonl, verify_frozen
from baby_boon.data import write_corpus
from baby_boon.style import reject_reasons

SOURCE = ROOT / "configs/authored_v1.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/authored-v1")
    a = ap.parse_args()
    verify_frozen()
    out = ROOT / a.out
    if (out / "manifest.json").exists(): raise FileExistsError("Refusing to replace an authored corpus")
    rows = read_jsonl(SOURCE)
    # Merging looks categories up by prompt id, so an id may only reuse a teacher prompt verbatim.
    teacher = {p["id"]: p for p in read_jsonl(ROOT / "configs/teacher_prompts.jsonl")}
    clashes = [r["id"] for r in rows if r["id"] in teacher and
               (teacher[r["id"]]["category"], teacher[r["id"]]["messages"]) != (r["category"], r["messages"])]
    if clashes: raise SystemExit(f"Ids clash with different teacher prompts: {clashes}")
    rejected = {r["id"]: reasons for r in rows if (reasons := reject_reasons(r["answer"], r["category"]))}
    if rejected: raise SystemExit(f"Style rejections: {rejected}")
    # Same holdout as teacher-v3: prompts 35-40 of each family are validation.
    examples = [{"id": f"{r['id']}-0", "family": r["id"], "split": "validation" if int(r["id"][2:]) >= 35 else "train",
                 "messages": r["messages"], "answer": r["answer"], "cue": r["cue"]} for r in rows]
    out.mkdir(parents=True, exist_ok=True)
    write_corpus(out, examples, {"source": "authored-v1", "author": "Claude (claude-opus-5-5) in a Claude Code session",
        "private_data": False, "external_dataset_rows": 0, "teacher_model": None,
        "admission": "Authored to the prompt expectations and style filters; not human-authored or independently reviewed.",
        "authored_sha256": digest(SOURCE), "builder_sha256": digest(Path(__file__))})


if __name__ == "__main__": main()
