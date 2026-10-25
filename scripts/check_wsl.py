import importlib.metadata as m
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "GPU-e995b393-4b89-9733-2d7b-8eb8b3064165"
for name in ["torch", "transformers", "peft", "accelerate", "psutil", "numpy"]:
    try:
        print(name, m.version(name), flush=True)
    except m.PackageNotFoundError:
        print(name, "missing", flush=True)
import torch
print("CUDA", torch.cuda.is_available(), torch.cuda.device_count(), flush=True)
if torch.cuda.is_available():
    x = torch.ones((16,16), device="cuda", requires_grad=True)
    (x @ x).sum().backward()
    print("GPU forward/backward", x.grad.isfinite().all().item(), flush=True)
