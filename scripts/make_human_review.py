"""Build the blinded human review page for a cases.jsonl (id, category, user, A, B; the A/B key stays in key.json, never
in the page). Ratings save per reviewer to the artifact's db at reviews/<viewer id>; only the owner reads them all."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "scripts/human_review_template.html"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="evidence/v12-unseen/cases.jsonl")
    ap.add_argument("--round", default="v12")
    ap.add_argument("--out", default="evidence/v12-unseen/human-review.html")
    a = ap.parse_args()
    cases = [json.loads(l) for l in (ROOT / a.cases).read_text(encoding="utf-8").splitlines() if l.strip()]
    # Robot deployment is deferred (2026-10-26): review plain chat only.
    cases = [c for c in cases if not c["user"].startswith("[Robot context")]
    data = json.dumps({"round": a.round, "cases": cases}, ensure_ascii=False).replace("</", "<\\/")
    (ROOT / a.out).write_text(TEMPLATE.read_text(encoding="utf-8").replace("__REVIEW_DATA__", data), encoding="utf-8")
    print(f"{a.out}: {len(cases)} cases")


if __name__ == "__main__": main()
