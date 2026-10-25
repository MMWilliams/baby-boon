from .common import prompt_ids


def encode_example(tokenizer, row, max_length=512):
    prefix = prompt_ids(tokenizer, row["messages"], row["system"])
    target = tokenizer.encode(row["target"], add_special_tokens=False) + [tokenizer.eos_token_id]
    if not prefix or not target or len(prefix) + len(target) > max_length:
        raise ValueError(f"Invalid or overlength example {row.get('id')}; no silent truncation")
    return {"input_ids": prefix + target, "labels": [-100]*len(prefix)+target,
            "attention_mask": [1]*(len(prefix)+len(target))}


def pad_batch(rows, pad_id):
    import torch
    length = max(len(r["input_ids"]) for r in rows)
    return {name: torch.tensor([r[name]+[value]*(length-len(r[name])) for r in rows], dtype=torch.long)
            for name,value in [("input_ids",pad_id),("labels",-100),("attention_mask",0)]}
