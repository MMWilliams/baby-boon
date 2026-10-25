"""Pin publisher metadata/cards without downloading weights or dialogue rows."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
LOCK = EVIDENCE / "source-lock.json"
SOURCES = [
    ("model", "HuggingFaceTB/SmolLM2-360M-Instruct", "baseline_candidate"),
    ("model", "Qwen/Qwen3-0.6B", "baseline_candidate"),
    ("model", "Qwen/Qwen3.5-0.8B", "reserve_candidate"),
    ("dataset", "OpenAssistant/oasst1", "review_pending"),
    ("dataset", "HuggingFaceTB/smoltalk", "constituent_review_pending"),
    ("dataset", "HuggingFaceH4/ultrachat_200k", "provenance_review_pending"),
    ("dataset", "facebook/empathetic_dialogues", "excluded_noncommercial"),
]


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "baby-boon-source-audit"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise RuntimeError(f"Metadata exceeds size budget: {url}")
            return data
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise RuntimeError("Download attempts exhausted")


def pin(source):
    kind, repo_id, status = source
    endpoint = "models" if kind == "model" else "datasets"
    metadata = json.loads(download(f"https://huggingface.co/api/{endpoint}/{repo_id}"))
    revision = metadata["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError(f"Unrecognized source revision: {repo_id}")
    prefix = "" if kind == "model" else "datasets/"
    base = f"https://huggingface.co/{prefix}{repo_id}/resolve/{revision}/"
    directory = EVIDENCE / (kind + "--" + repo_id.replace("/", "--"))
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    config = None
    for filename in (["README.md", "config.json"] if kind == "model" else ["README.md"]):
        url = base + filename
        data = download(url)
        path = directory / filename
        path.write_bytes(data)
        files.append({"path": path.relative_to(ROOT).as_posix(), "url": url,
                      "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        if filename == "config.json":
            config = json.loads(data)
    record = {
        "kind": kind, "id": repo_id, "revision": revision, "status": status,
        "declared_license": metadata.get("cardData", {}).get("license"),
        "publisher_url": f"https://huggingface.co/{prefix}{repo_id}",
        "files": files,
    }
    if config is not None:
        record["model_type"] = config.get("model_type")
        record["architectures"] = config.get("architectures")
        record["safetensors_metadata"] = metadata.get("safetensors")
    return record


def verify():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = {(kind, repo_id) for kind, repo_id, _ in SOURCES}
    actual = {(item["kind"], item["id"]) for item in lock["sources"]}
    if actual != expected or len(lock["sources"]) != len(expected):
        raise RuntimeError("Source inventory differs from the declared shortlist")
    count = 0
    for source in lock["sources"]:
        if not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
            raise RuntimeError("Source revision is not a pinned commit")
        for item in source["files"]:
            path = (ROOT / item["path"]).resolve()
            if not path.is_relative_to(EVIDENCE.resolve()):
                raise RuntimeError("Evidence path escapes the evidence directory")
            data = path.read_bytes()
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise RuntimeError(f"Evidence mismatch: {item['path']}")
            count += 1
    print(f"PASS: {len(actual)} pinned source records and {count} evidence files verified; no training/data-quality claim")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--verify-only", action="store_true")
    group.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        verify()
        return
    if LOCK.exists() and not args.refresh:
        raise SystemExit("A source lock already exists. Use --verify-only or an intentional --refresh.")
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(pin, SOURCES))
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "publisher metadata, model configs and cards only; no weights or dialogue rows",
              "sources": records}
    LOCK.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for record in records:
        print(f"{record['id']} @ {record['revision']}: declared license={record['declared_license']}; {record['status']}")
    verify()


if __name__ == "__main__":
    main()
