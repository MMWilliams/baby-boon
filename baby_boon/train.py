"""Bounded CPU or single-GPU LoRA pilot with assistant-only loss and immutable provenance."""
import argparse
import json
import platform
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .common import ROOT, ResourceGuard, configure_cpu, configure_gpu, digest, read_jsonl, source, verify_frozen, write_json
from .data import audit
from .training_data import encode_example, pad_batch


def run_environment(torch):
    import peft
    import transformers
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    cuda = torch.cuda.is_available()
    return {"started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": git("rev-parse", "HEAD"),
            "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no")), "host": platform.node(),
            "python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__,
            "peft": peft.__version__, "cuda_runtime": torch.version.cuda if cuda else None,
            "gpu_name": torch.cuda.get_device_name(0) if cuda else None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen3-0.6B")
    p.add_argument("--data", default="data/pilot-v1")
    p.add_argument("--out", required=True)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--max-steps", type=int, default=80)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--seed", type=int, default=20261025)
    p.add_argument("--eval-every", type=int, default=40, help="validation loss every N steps (0: before and after only)")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out/"config.json").exists():
        raise FileExistsError("Use a new checkpoint directory for each run")
    verify_frozen()
    audit(args.data)
    torch = configure_cpu() if args.device == "cpu" else configure_gpu()
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    from peft import LoraConfig, get_peft_model
    set_seed(args.seed)
    guard = ResourceGuard(out/"resources.json", max_seconds=1800)
    start = time.monotonic()
    s = source(args.model)
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=s["revision"])
    model = AutoModelForCausalLM.from_pretrained(args.model, revision=s["revision"], dtype=torch.bfloat16, attn_implementation="sdpa").to(args.device)
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(r=8,lora_alpha=16,lora_dropout=0.05,target_modules="all-linear",task_type="CAUSAL_LM"))
    train = [encode_example(tokenizer,r) for r in read_jsonl(Path(args.data)/"train.jsonl")]
    valid = [encode_example(tokenizer,r) for r in read_jsonl(Path(args.data)/"validation.jsonl")]
    params = [v for v in model.parameters() if v.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=8e-5, weight_decay=0.01)
    write_json(out/"config.json", {**vars(args),"base_revision":s["revision"],"threads":6,
        "device":args.device, "dtype":f"bf16 base, {args.device} bf16 autocast, float32 adapters", "learning_rate":8e-5,
        "lora_rank":8,"lora_alpha":16,"lora_dropout":0.05,"target_modules":"all-linear",
        "microbatch":2,"gradient_accumulation":4,"trainable_parameters":sum(v.numel() for v in params),
        "data_manifest_sha256":digest(Path(args.data)/"manifest.json"),"dev_sha256":digest(ROOT/"eval/dev.jsonl"),
        "train_code_sha256":digest(Path(__file__)),"lock_sha256":digest(ROOT/"uv.lock"),
        "train_examples":len(train),"validation_examples":len(valid),"effective_batch":8,"gradient_clip":1.0,
        "lr_schedule":"constant","eval_every":args.eval_every,
        "optimizer":{"type":"AdamW",**{k:optimizer.defaults[k] for k in ("lr","betas","eps","weight_decay")}},
        **run_environment(torch)})

    def to_device(batch):
        return {k: v.to(args.device) for k, v in batch.items()}

    def evaluate_loss():
        model.eval()
        weighted,total = 0.0,0
        with torch.inference_mode(), torch.autocast(args.device, dtype=torch.bfloat16):
            for at in range(0,len(valid),2):
                batch = to_device(pad_batch(valid[at:at+2], tokenizer.eos_token_id))
                result = model(**batch)
                count = int((batch["labels"][:,1:] != -100).sum())
                if not torch.isfinite(result.loss): raise RuntimeError("Nonfinite validation loss")
                weighted += float(result.loss)*count
                total += count
        return weighted/total

    step,seen = 0,0
    with (out/"train.jsonl").open("w",encoding="utf-8",buffering=1) as log:
        def emit(record):
            record["elapsed_seconds"] = time.monotonic()-start
            log.write(json.dumps(record)+"\n")
            print(json.dumps(record),flush=True)

        def log_eval():
            loss = evaluate_loss()
            emit({"event":"eval","step":step,"validation_loss":loss})
            return loss

        before = log_eval()
        for epoch in range(args.epochs):
            random.Random(args.seed+epoch).shuffle(train)
            for at in range(0,len(train),8):
                if step >= args.max_steps: break
                step_start = time.monotonic()
                model.train()
                optimizer.zero_grad(set_to_none=True)
                group = train[at:at+8]
                target_count = sum(sum(x != -100 for x in r["labels"][1:]) for r in group)
                running,input_tokens = 0.0,0
                for mb in range(0,len(group),2):
                    batch = to_device(pad_batch(group[mb:mb+2],tokenizer.eos_token_id))
                    input_tokens += int(batch["attention_mask"].sum())
                    count = int((batch["labels"][:,1:] != -100).sum())
                    with torch.autocast(args.device,dtype=torch.bfloat16):
                        loss = model(**batch).loss * (count/target_count)
                    if not torch.isfinite(loss): raise RuntimeError("Nonfinite training loss")
                    loss.backward()
                    running += float(loss.detach())
                norm = torch.nn.utils.clip_grad_norm_(params,1.0,error_if_nonfinite=True)
                optimizer.step()
                if args.device == "cuda": torch.cuda.synchronize()
                step += 1
                seen += len(group)
                seconds = time.monotonic()-step_start
                record = {"event":"step","step":step,"epoch":epoch+1,"examples_seen":seen,"loss":running,
                          "gradient_norm":float(norm),"learning_rate":optimizer.param_groups[0]["lr"],
                          "target_tokens":target_count,"input_tokens":input_tokens,"step_seconds":seconds,
                          "tokens_per_second":input_tokens/seconds,"rss_mib":guard.process.memory_info().rss/2**20}
                if args.device == "cuda":
                    record |= {"gpu_peak_allocated_mib":torch.cuda.max_memory_allocated()/2**20,
                               "gpu_reserved_mib":torch.cuda.memory_reserved()/2**20}
                    torch.cuda.reset_peak_memory_stats()
                emit(record)
                if args.eval_every and step % args.eval_every == 0 and step < args.max_steps: log_eval()
            if step >= args.max_steps: break
        after = log_eval()
    lora_b_norm = sum(float(v.detach().float().square().sum()) for n,v in model.named_parameters() if "lora_B" in n)**0.5
    if not lora_b_norm > 0: raise RuntimeError("LoRA B remains at zero; no update")
    model.save_pretrained(out/"adapter")
    tokenizer.save_pretrained(out/"adapter")
    write_json(out/"result.json",{"steps":step,"validation_loss_before":before,"validation_loss_after":after,
        "lora_b_norm_from_zero_init":lora_b_norm,"elapsed_seconds":time.monotonic()-start,
        "conclusion":"Optimization evidence only; social improvement requires independent review"})
    guard.close()
    print("SAVED",out,"validation",before,"->",after,flush=True)


if __name__ == "__main__": main()
