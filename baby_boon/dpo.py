"""DPO (direct preference optimization) on top of a trained LoRA adapter: the adapter is trained further to prefer the
chosen reply over the reviewed rejected one. The reference is the starting adapter, so its log-probabilities are
computed once before any update."""
import argparse
import json
import random
import time
from pathlib import Path

from .common import ROOT, SYSTEM, ResourceGuard, configure_gpu, digest, read_jsonl, source, verify_frozen, write_json
from .training_data import encode_example, pad_batch


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen3-1.7B")
    p.add_argument("--adapter", default="checkpoints/pilot-v4-1.7b/adapter")
    p.add_argument("--pairs", default="configs/dpo_v1.jsonl")
    p.add_argument("--out", required=True)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--beta", type=float, default=0.1)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--seed", type=int, default=20261025)
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "config.json").exists(): raise FileExistsError("Use a new checkpoint directory for each run")
    verify_frozen()
    torch = configure_gpu()
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    from peft import PeftModel
    set_seed(args.seed)
    guard = ResourceGuard(out / "resources.json", max_seconds=1800)
    start = time.monotonic()
    s = source(args.model)
    tok = AutoTokenizer.from_pretrained(args.model, revision=s["revision"])
    model = AutoModelForCausalLM.from_pretrained(args.model, revision=s["revision"], dtype=torch.bfloat16,
                                                 attn_implementation="sdpa").to("cuda")
    model = PeftModel.from_pretrained(model, ROOT / args.adapter, is_trainable=True)
    model.config.use_cache = False

    def encode(row, side):
        return encode_example(tok, {"id": row["id"], "messages": row["messages"], "system": SYSTEM, "target": row[side]})

    pairs = read_jsonl(ROOT / args.pairs)
    split = {name: [(encode(r, "chosen"), encode(r, "rejected")) for r in pairs if r["split"] == name]
             for name in ("train", "validation")}

    def logprobs(seqs):
        # Summed log-probability of each target reply given its prompt.
        batch = {k: v.to("cuda") for k, v in pad_batch(seqs, tok.eos_token_id).items()}
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits[:, :-1].float()
        labels = batch["labels"][:, 1:]
        mask = labels != -100
        picked = logits.log_softmax(-1).gather(-1, labels.clamp(min=0).unsqueeze(-1)).squeeze(-1)
        return (picked * mask).sum(-1)

    def pair_logprobs(group):
        lp = logprobs([c for c, _ in group] + [r for _, r in group])
        return lp[:len(group)], lp[len(group):]

    model.eval()
    with torch.inference_mode():
        reference = {name: [tuple(float(x) for x in pair_logprobs([pair])) for pair in rows]
                     for name, rows in split.items()}

    def validate():
        model.eval()
        margins, chosen_delta = [], []
        with torch.inference_mode():
            for pair, (rc, rr) in zip(split["validation"], reference["validation"]):
                pc, pr = (float(x) for x in pair_logprobs([pair]))
                margins.append((pc - rc) - (pr - rr))
                chosen_delta.append(pc - rc)
        return {"accuracy": sum(m > 0 for m in margins) / len(margins), "mean_margin": sum(margins) / len(margins),
                "mean_chosen_logprob_change": sum(chosen_delta) / len(chosen_delta)}

    params = [v for v in model.parameters() if v.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    write_json(out / "config.json", {**vars(args), "base_revision": s["revision"], "device": "cuda",
        "dtype": "bf16 base, cuda bf16 autocast, float32 adapters", "batch_pairs": 4,
        "train_pairs": len(split["train"]), "validation_pairs": len(split["validation"]),
        "pairs_sha256": digest(ROOT / args.pairs), "adapter_config_sha256": digest(ROOT / args.adapter / "adapter_config.json"),
        "dev_sha256": digest(ROOT / "eval/dev.jsonl"), "dpo_code_sha256": digest(Path(__file__)),
        "lock_sha256": digest(ROOT / "uv.lock")})
    before = validate()
    print("Validation before", before, flush=True)
    order = list(range(len(split["train"])))
    step = 0
    with (out / "train.jsonl").open("w", encoding="utf-8", buffering=1) as log:
        for epoch in range(args.epochs):
            random.Random(args.seed + epoch).shuffle(order)
            for at in range(0, len(order), 4):
                idx = order[at:at + 4]
                model.train()
                optimizer.zero_grad(set_to_none=True)
                pc, pr = pair_logprobs([split["train"][i] for i in idx])
                rc = torch.tensor([reference["train"][i][0] for i in idx], device="cuda")
                rr = torch.tensor([reference["train"][i][1] for i in idx], device="cuda")
                margin = (pc - rc) - (pr - rr)
                loss = -torch.nn.functional.logsigmoid(args.beta * margin).mean()
                if not torch.isfinite(loss): raise RuntimeError("Nonfinite DPO loss")
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(params, 1.0, error_if_nonfinite=True)
                optimizer.step()
                step += 1
                record = {"step": step, "epoch": epoch + 1, "loss": float(loss), "accuracy": float((margin > 0).float().mean()),
                          "mean_margin": float(margin.mean()), "gradient_norm": float(norm),
                          "elapsed_seconds": time.monotonic() - start}
                log.write(json.dumps(record) + "\n")
                print(json.dumps(record), flush=True)
    after = validate()
    model.save_pretrained(out / "adapter")
    tok.save_pretrained(out / "adapter")
    write_json(out / "result.json", {"steps": step, "validation_before": before, "validation_after": after,
        "elapsed_seconds": time.monotonic() - start,
        "conclusion": "Preference-fit evidence only; social improvement requires dev review"})
    guard.close()
    print("SAVED", out, "validation", before, "->", after, flush=True)


if __name__ == "__main__": main()
