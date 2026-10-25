"""Pin, download, verify and convert the non-thinking CPU teacher to Q8_0 GGUF."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baby_boon.common import digest, write_json

REPO = "Qwen/Qwen3-4B-Instruct-2507"
REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
DEST = ROOT / "models/teacher-qwen3-4b-instruct-2507"
EVIDENCE = ROOT / "evidence/model--Qwen--Qwen3-4B-Instruct-2507"
CARD_FILES = ["README.md", "LICENSE", "config.json", "generation_config.json", "tokenizer_config.json"]
CONVERTER = ROOT / "tools/llama/source/llama.cpp-184f6536024668e8908ab8c86033d56708e62b40/convert_hf_to_gguf.py"


def fetch(url, path=None):
    request = urllib.request.Request(url, headers={"User-Agent": "baby-boon-teacher-pin"})
    h = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=60) as response:
        if path is None:
            return response.read()
        with open(path, "wb") as f:
            for block in iter(lambda: response.read(8 * 1024 * 1024), b""):
                h.update(block)
                f.write(block)
    return h.hexdigest()


def main():
    meta = json.loads(fetch(f"https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true"))
    if meta["sha"] != REVISION or meta.get("cardData", {}).get("license") != "apache-2.0" or meta.get("gated"):
        raise RuntimeError("Teacher revision, license or access changed")
    files = [s for s in meta["siblings"] if s["rfilename"] != ".gitattributes"]
    shards = [s for s in files if s["rfilename"].endswith(".safetensors")]
    src = DEST / "src"
    gguf = DEST / "model-q8_0.gguf"
    if gguf.exists():
        raise FileExistsError("Teacher GGUF already exists")
    src.mkdir(parents=True, exist_ok=True)
    missing = sum(s["size"] for s in shards if not (src / s["rfilename"]).exists())
    # Shards plus a ~4.3 GB Q8_0 output coexist until conversion ends; keep 2 GiB for other jobs.
    need = missing + int(4.6 * 1024**3) + 2 * 1024**3
    if shutil.disk_usage(DEST).free < need:
        raise RuntimeError(f"Need {need / 1024**3:.1f} GiB free before download")
    records = []
    for s in files:
        name = s["rfilename"]
        path = src / name
        url = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}"
        actual = digest(path) if path.exists() else fetch(url, path)
        expected = (s.get("lfs") or {}).get("sha256")
        if path.stat().st_size != s["size"] or (expected and actual != expected):
            raise RuntimeError(f"Teacher file mismatch: {name}")
        records.append({"path": name, "url": url, "bytes": s["size"], "sha256": actual,
                        "git_blob_id": s.get("blobId"), "publisher_lfs_sha256_verified": bool(expected)})
        print("verified", name, flush=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name in CARD_FILES:
        shutil.copyfile(src / name, EVIDENCE / name)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    with (DEST / "convert.log").open("w", encoding="utf-8") as f:
        subprocess.run([sys.executable, str(CONVERTER), str(src), "--outfile", str(gguf), "--outtype", "q8_0"],
                       env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
    # Shards are hash-pinned and re-downloadable; the drive cannot hold them beside other work.
    for s in shards:
        (src / s["rfilename"]).unlink()
    lock = {"id": REPO, "revision": REVISION, "declared_license": "apache-2.0",
            "role": "CPU teacher candidate; outputs require review before any training admission",
            "files": records, "llama_lock_sha256": digest(ROOT / "evidence/llama-lock.json"),
            "converter_sha256": digest(CONVERTER), "outtype": "q8_0",
            "gguf": {"path": gguf.relative_to(ROOT).as_posix(), "bytes": gguf.stat().st_size, "sha256": digest(gguf)},
            "shards_deleted_after_conversion": True}
    write_json(ROOT / "evidence/teacher-lock.json", lock)
    print("Teacher GGUF ready:", gguf, round(gguf.stat().st_size / 1024**2, 1), "MiB", flush=True)


if __name__ == "__main__":
    main()
