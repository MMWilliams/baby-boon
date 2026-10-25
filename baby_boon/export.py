import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .common import ROOT, configure_cpu, digest, source, write_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen3-0.6B")
    p.add_argument("--checkpoint")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    dest = Path(a.out).resolve()
    dest.mkdir(parents=True,exist_ok=True)
    if (dest/"model-q4_k_m.gguf").exists(): raise FileExistsError("Export already exists")
    torch = configure_cpu()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    s = source(a.model)
    # Normalize both sides through the same HF save path. The original Qwen
    # safetensors contains identical tied input/output weights twice; preserving
    # both only on the base changes GGUF quantizer policy and invalidates parity.
    model = AutoModelForCausalLM.from_pretrained(a.model,revision=s["revision"],dtype=torch.float32)
    if a.checkpoint:
        config = json.loads((Path(a.checkpoint)/"config.json").read_text())
        if config["model"] != a.model or config["base_revision"] != s["revision"]:
            raise ValueError("Adapter/base revision mismatch")
        model = PeftModel.from_pretrained(model,Path(a.checkpoint)/"adapter")
        model = model.merge_and_unload(safe_merge=True)
    model = model.to(torch.bfloat16)
    source_dir = dest/"merged"
    model.save_pretrained(source_dir)
    AutoTokenizer.from_pretrained(a.model,revision=s["revision"]).save_pretrained(source_dir)
    del model
    converter = ROOT/"tools/llama/source/llama.cpp-184f6536024668e8908ab8c86033d56708e62b40/convert_hf_to_gguf.py"
    full = dest/"model-f16.gguf"
    quant = dest/"model-q4_k_m.gguf"
    env = {**os.environ,"PYTHONIOENCODING":"utf-8"}
    with (dest/"convert.log").open("w",encoding="utf-8") as f:
        subprocess.run([sys.executable,str(converter),str(source_dir),"--outfile",str(full),"--outtype","f16"],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (dest/"quantize.log").open("w",encoding="utf-8") as f:
        subprocess.run([str(ROOT/"tools/llama/runtime/llama-quantize.exe"),str(full),str(quant),"Q4_K_M","6"],stdout=f,stderr=subprocess.STDOUT,check=True)
    write_json(dest/"manifest.json", {"base_model":a.model,"base_revision":s["revision"],"checkpoint":a.checkpoint,
        "llama_lock_sha256":digest(ROOT/"evidence/llama-lock.json"),"converter_sha256":digest(converter),
        "quantization":"Q4_K_M","normalization":"HF save_pretrained BF16, preserving tied tensor sharing",
        "files":{x.name:{"bytes":x.stat().st_size,"sha256":digest(x)} for x in [full,quant]}})
    print("Exported",quant,quant.stat().st_size/1024**2,"MiB",flush=True)


if __name__ == "__main__": main()
