"""Fetch the published GGUF and run llama-server for it, so `baby-boon` works right after a pip install."""
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from .common import digest

MODEL_URL = "https://huggingface.co/maureesewilliams/baby-boon/resolve/main/model-q4_k_m.gguf"
MODEL_SHA256 = "11976e2618aee889124cabb2a7235b104b6cb5b2c1b2750e93edf26ec74aaaf6"
HOME = Path(os.environ.get("BABY_BOON_HOME") or Path.home() / ".cache" / "baby-boon")


def model_path():
    path = HOME / "model-q4_k_m.gguf"
    if not path.exists():
        HOME.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".part")
        print(f"Downloading the model (1.1 GB) to {path}", file=sys.stderr)
        urllib.request.urlretrieve(MODEL_URL, part)
        if digest(part) != MODEL_SHA256:
            part.unlink()
            raise SystemExit("The downloaded model failed its sha256 check; run again to retry.")
        part.replace(path)
    return path


def wait_ready(proc, url, log):
    deadline = time.monotonic() + 300
    while proc.poll() is None:
        try:
            with urllib.request.urlopen(url + "/health", timeout=2):
                return
        except OSError:
            if time.monotonic() > deadline:
                raise SystemExit(f"llama-server didn't load the model in 5 minutes; see {log}")
            time.sleep(0.5)
    raise SystemExit(f"llama-server exited with code {proc.returncode}; see {log}")


@contextmanager
def server(binary=None):
    """Start llama-server with the published model on a free local port; yields its URL."""
    name = binary or os.environ.get("BABY_BOON_LLAMA_SERVER") or "llama-server"
    # Windows can't launch a relative path written with forward slashes, so resolve paths before which().
    binary = shutil.which(os.path.abspath(name) if os.path.dirname(name) else name)
    if not binary:
        raise SystemExit("llama-server not found. Install llama.cpp (winget install llama.cpp, brew install llama.cpp) "
                         "or pass --llama-server PATH.")
    model = model_path()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url, log = f"http://127.0.0.1:{port}", HOME / "llama-server.log"
    # Same settings as scripts/serve.ps1, where every evaluation ran (CPU, one slot, 2,048-token context).
    with open(log, "wb") as out:
        proc = subprocess.Popen([binary, "-m", str(model), "-ngl", "0", "-c", "2048", "-np", "1",
                                 "--host", "127.0.0.1", "--port", str(port), "--jinja"], stdout=out, stderr=subprocess.STDOUT)
        try:
            wait_ready(proc, url, log)
            yield url
        finally:
            proc.terminate()
            proc.wait()
