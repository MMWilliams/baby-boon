"""Greedy replies from 1.7B adapters on held-out authored pt prompts (pt35-40) plus two d15-like probes, to check
whether a family was learned before spending a dev review. Usage: probe_heldout.py <adapter dir>..."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from baby_boon.common import configure_gpu, prompt_ids, read_jsonl, source
torch = configure_gpu()
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
s = source("Qwen/Qwen3-1.7B")
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B", revision=s["revision"])
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-1.7B", revision=s["revision"], dtype=torch.float32).to("cuda")
cases = [r for r in read_jsonl(Path(__file__).resolve().parents[1] / "configs/authored_v2.jsonl") if int(r["id"][2:]) >= 35]
cases += [{"id": "x1", "messages": [{"role": "user", "content": "Shattered. Tell me one small nice thing."}]},
          {"id": "x2", "messages": [{"role": "user", "content": "I'm too worn out to talk much. Something pleasant, please."}]}]
for adapter in sys.argv[1:]:
    model = PeftModel.from_pretrained(base, adapter).eval()
    for c in cases:
        ids = torch.tensor([prompt_ids(tok, c["messages"])], device="cuda")
        with torch.inference_mode():
            out = model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=80, do_sample=False, pad_token_id=tok.eos_token_id)
        print(Path(adapter).parent.name, c["id"], tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True), flush=True)
    base = model.unload()
