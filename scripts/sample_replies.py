"""Sample replies from a 1.7B adapter on low_energy prompts (authored pt + teacher le) as candidate rejected replies
for preference pairs. Output is a draft: every rejected reply is reviewed before it enters configs/dpo_*.jsonl."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baby_boon.common import configure_gpu, prompt_ids, read_jsonl, source


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="checkpoints/pilot-v4-1.7b/adapter")
    ap.add_argument("--out", default="runs/dpo-candidates-v1.jsonl")
    ap.add_argument("--samples", type=int, default=6)
    a = ap.parse_args()
    out = ROOT / a.out
    if out.exists(): raise FileExistsError("Use a new candidates file")
    torch = configure_gpu()
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    from peft import PeftModel
    set_seed(20261026)
    s = source("Qwen/Qwen3-1.7B")
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B", revision=s["revision"])
    model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-1.7B", revision=s["revision"], dtype=torch.bfloat16).to("cuda")
    model = PeftModel.from_pretrained(model, ROOT / a.adapter).eval()
    prompts = read_jsonl(ROOT / "configs/authored_v2.jsonl")
    prompts += [p for p in read_jsonl(ROOT / "configs/teacher_prompts.jsonl") if p["category"] == "low_energy"]
    with out.open("w", encoding="utf-8") as f:
        for p in prompts:
            ids = torch.tensor([prompt_ids(tok, p["messages"])], device="cuda")
            with torch.inference_mode():
                gen = model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=80, do_sample=True,
                                     temperature=0.9, top_p=0.95, num_return_sequences=a.samples, pad_token_id=tok.eos_token_id)
            texts = sorted({tok.decode(g[ids.shape[1]:], skip_special_tokens=True).strip() for g in gen})
            f.write(json.dumps({"id": p["id"], "messages": p["messages"], "samples": texts}, ensure_ascii=False) + "\n")
            print(p["id"], len(texts), flush=True)


if __name__ == "__main__": main()
