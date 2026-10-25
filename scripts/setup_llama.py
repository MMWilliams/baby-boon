"""Fetch a pinned official CPU runtime and matching conversion source."""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = "b11829"
COMMIT = "184f6536024668e8908ab8c86033d56708e62b40"
DIGEST = "c534f35ce9c842f3bc224fadaecc82e1b49768f63e8320922f6dbd603f66395e"
DEST = ROOT / "tools/llama"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    records = []
    for name, url, expected in [
        ("runtime.zip", f"https://github.com/ggml-org/llama.cpp/releases/download/{TAG}/llama-{TAG}-bin-win-cpu-x64.zip", DIGEST),
        ("source.zip", f"https://github.com/ggml-org/llama.cpp/archive/{COMMIT}.zip", None),
    ]:
        path = DEST / name
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected and actual != expected:
            raise RuntimeError(f"Digest mismatch for {name}")
        folder = DEST / ("runtime" if name == "runtime.zip" else "source")
        folder.mkdir(exist_ok=True)
        with zipfile.ZipFile(path) as z:
            # Reject path traversal before extraction.
            for member in z.namelist():
                if not (folder / member).resolve().is_relative_to(folder.resolve()):
                    raise RuntimeError("Unsafe archive member")
            z.extractall(folder)
        records.append({"url": url, "sha256": actual, "publisher_digest_verified": bool(expected)})
    (ROOT / "evidence/llama-lock.json").write_text(json.dumps({"tag": TAG, "commit": COMMIT, "files": records}, indent=2)+"\n")
    print("Pinned CPU runtime and source ready:", DEST)


if __name__ == "__main__":
    main()
