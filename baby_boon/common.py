import hashlib
import json
import os
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GPU_UUID = "GPU-e995b393-4b89-9733-2d7b-8eb8b3064165"
SYSTEM = (
    "You are Baby Boon, a conversational AI. Be warm, natural, concise and attentive "
    "to the user's actual words. Match their energy; ordinary chat need not become "
    "counseling. Use humor when welcome, respect corrections and requests to stop, "
    "and disagree kindly when appropriate. Do not claim feelings, observations, "
    "memories or physical actions you do not have. Treat guesses about emotions "
    "as uncertain. Usually reply in one to three short sentences."
)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def source(model):
    sources = json.loads((ROOT / "evidence/source-lock.json").read_text())["sources"]
    return next(s for s in sources if s["id"] == model)


def verify_frozen():
    for name, expected in json.loads((ROOT / "eval/frozen.json").read_text()).items():
        if digest(ROOT / name.replace("\\", "/")) != expected:
            raise ValueError(f"Frozen development file changed: {name}")


def configure_gpu():
    # Mask before importing torch; CUDA's device 0 is this explicit physical UUID.
    os.environ["CUDA_VISIBLE_DEVICES"] = GPU_UUID
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    import torch
    torch.set_num_threads(6)
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("Expected exactly one visible CUDA GPU")
    total = torch.cuda.get_device_properties(0).total_memory
    # Leave margin for the context and non-PyTorch CUDA allocations.
    torch.cuda.set_per_process_memory_fraction(14500 * 1024**2 / total)
    free, _ = torch.cuda.mem_get_info()
    if free < 8 * 1024**3:
        raise RuntimeError("Less than 8 GiB free GPU memory; defer this job")
    return torch


def configure_cpu():
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    import torch
    torch.set_num_threads(6)
    torch.set_num_interop_threads(1)
    return torch


class ResourceGuard:
    """Sample host RSS/commit and torch allocation; fail only this process on excess."""

    def __init__(self, path, max_seconds=1800):
        import psutil
        self.process = psutil.Process()
        self.path = Path(path)
        self.started = time.monotonic()
        self.max_seconds = max_seconds
        self.stop = threading.Event()
        self.report = {"visible_gpu": os.environ.get("CUDA_VISIBLE_DEVICES"), "peak_rss_mib": 0, "peak_gpu_reserved_mib": 0,
                       "peak_gpu_allocated_mib": 0, "status": "running"}
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def sample(self):
        import psutil
        import torch
        rss = self.process.memory_info().rss / 1024**2
        reserved = torch.cuda.memory_reserved() / 1024**2 if torch.cuda.is_available() else 0
        allocated = torch.cuda.memory_allocated() / 1024**2 if torch.cuda.is_available() else 0
        self.report["peak_rss_mib"] = max(rss, self.report["peak_rss_mib"])
        self.report["peak_gpu_reserved_mib"] = max(reserved, self.report["peak_gpu_reserved_mib"])
        self.report["peak_gpu_allocated_mib"] = max(allocated, self.report["peak_gpu_allocated_mib"])
        elapsed = time.monotonic() - self.started
        self.report["elapsed_seconds"] = elapsed
        if rss > 20000 or reserved > 14500 or elapsed > self.max_seconds or psutil.virtual_memory().available < 2 * 1024**3:
            self.report["status"] = "resource_limit_exceeded"
            write_json(self.path, self.report)
            os._exit(75)

    def _run(self):
        while not self.stop.wait(1):
            self.sample()

    def close(self):
        self.stop.set()
        self.thread.join()
        self.sample()
        self.report["status"] = "completed"
        write_json(self.path, self.report)


def prompt_ids(tokenizer, messages, system=SYSTEM):
    return tokenizer.apply_chat_template(
        [{"role": "system", "content": system}] + messages,
        tokenize=True, add_generation_prompt=True, enable_thinking=False,
    )
