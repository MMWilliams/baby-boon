"""Collect complete GPU development responses; CPU timing is a separate check."""
import argparse
import json
import time
import sys
from pathlib import Path

from .common import ROOT, SYSTEM, ResourceGuard, configure_cpu, configure_gpu, digest, prompt_ids, read_jsonl, source, verify_frozen, write_json


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--adapter")
    p.add_argument("--out", required=True)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = p.parse_args()
    verify_frozen()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "responses.jsonl").exists():
        raise FileExistsError("Do not overwrite an evaluation journal")
    torch = configure_cpu() if args.device == "cpu" else configure_gpu()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    s = source(args.model)
    guard = ResourceGuard(out / "resources.json")
    started = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(args.model, revision=s["revision"])
    dtype = torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model, revision=s["revision"], dtype=dtype, attn_implementation="sdpa").to(args.device)
    if args.adapter:
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    load_s = time.perf_counter() - started
    write_json(out / "config.json", {"model": args.model, "revision": s["revision"], "adapter": args.adapter,
               "system": SYSTEM, "max_new_tokens": 128, "do_sample": False, "enable_thinking": False,
               "dev_sha256": digest(ROOT / "eval/dev.jsonl"), "load_seconds_including_download": load_s,
               "device": args.device, "dtype": str(dtype), "threads": 6,
               "timing_scope": "Development inference only; quantized deployment benchmark is separate"})
    with (out / "responses.jsonl").open("w", encoding="utf-8", buffering=1) as f:
        for case in read_jsonl(ROOT / "eval/dev.jsonl"):
            record = dict(case)
            try:
                ids = torch.tensor([prompt_ids(tok, case["messages"])], device=args.device)
                if args.device == "cuda": torch.cuda.synchronize()
                start = time.perf_counter()
                with torch.inference_mode():
                    result = model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=128,
                                            do_sample=False, pad_token_id=tok.eos_token_id)
                if args.device == "cuda": torch.cuda.synchronize()
                gen = result[0, ids.shape[1]:].tolist()
                record.update(text=tok.decode(gen, skip_special_tokens=True), token_ids=gen, prompt_tokens=ids.shape[1],
                              seconds=time.perf_counter()-start, truncated=len(gen)==128 and gen[-1]!=tok.eos_token_id,
                              error=None)
            except Exception as exc:
                record.update(error=repr(exc))
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(case["id"], record.get("text", record.get("error")), flush=True)
    guard.close()


if __name__ == "__main__":
    main()
