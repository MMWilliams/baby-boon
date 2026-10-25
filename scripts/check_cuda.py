import ctypes
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "GPU-e995b393-4b89-9733-2d7b-8eb8b3064165"
print("Loading Linux CUDA driver", flush=True)
cuda = ctypes.CDLL("libcuda.so.1")
print("cuInit", cuda.cuInit(0), flush=True)
count = ctypes.c_int()
print("cuDeviceGetCount", cuda.cuDeviceGetCount(ctypes.byref(count)), count.value, flush=True)
