---
license: apache-2.0
base_model: Qwen/Qwen3-1.7B
language:
- en
pipeline_tag: text-generation
tags:
- gguf
- llama.cpp
- lora
- qwen3
- conversational
- cpu
---

# Baby Boon

A small local social chat model: Qwen3-1.7B fine-tuned with LoRA (rank 8), merged and quantized to Q4_K_M. The GGUF is
1.1 GB, needs about 2 GB of RAM, and runs at about 30 tokens/s on a desktop CPU (Ryzen 9 9900X, 6 threads). Replies
end with a tone and expression cue for a voice or an avatar.

**Not for medical, emergency or crisis use.** Run it with the guards in the `baby-boon` Python package. On 40 fresh
prompts with the guards on, 5 of 12 health questions still got unsafe advice and 3 of 8 emergencies got a harmful
reply. The raw GGUF in another app has none of the guards and does worse.

## Use

```
pip install baby-boon
baby-boon
```

The client (Python 3.10+, no dependencies) downloads `model-q4_k_m.gguf` from this repo, checks its sha256, starts
llama.cpp's `llama-server` (install with `winget install llama.cpp` or `brew install llama.cpp`) and prints one JSON
line per turn: `text`, `tone`, `expression`, `intensity` (0-2), `cue_valid`. Code and the full research log:
[github.com/MMWilliams/baby-boon](https://github.com/MMWilliams/baby-boon).

The guards on every turn:
- Perception: a reply claiming to see or hear the user's surroundings is resampled, then replaced with an honest line.
- Facts: kitchen and temperature conversions are computed and given to the model; a reply with figures that aren't
  in the note or the message is resampled, then replaced by the note.
- Health: in a health context the model is told to refer rather than judge, and replies with a medicine, a dose, a
  severity verdict or a guessed condition are resampled, then replaced by a referral. Clear red flags (not
  breathing, unresponsive, a seizure, choking and similar) skip the model and get a fixed "call emergency services"
  line.

## Files

- `model-q4_k_m.gguf`: the model (sha256 `11976e2618aee889124cabb2a7235b104b6cb5b2c1b2750e93edf26ec74aaaf6`).
- `adapter/`: the LoRA adapter for `Qwen/Qwen3-1.7B` (PEFT 0.18.0) with the tokenizer and chat template.
- `manifest.json`: export provenance (base revision, llama.cpp lock, converter and file hashes).

## Training

782 conversations (1,350 training rows with plain and cue variants), one epoch, LoRA rank 8, learning rate 8e-5,
validation loss 5.74 to 1.68. 422 conversations came from Qwen3-4B-Instruct-2507 as a local teacher, filtered by
style rules and reviewed; 360 were written by Claude (claude-opus-5-5) in Claude Code sessions, covering practical
help, giving space, two-party situations, low energy, honesty about perception, and referring health questions. No
external conversation dataset, no private or personal data.

## Evaluation and limitations

Every gate was a fresh prompt set written by a separate AI agent that hadn't seen the repo, scored blind by another
agent against a fixed rubric. There was no human review. On the health set behind this release (12 health questions,
6 health venting, 8 emergencies, 14 controls), against the previous model v12 with the same guards:

| | v12 | this model (v14) |
|---|---|---|
| Unsafe replies | 11 | 8 |
| Emergency criticals | 5 | 3 |
| Unsafe health advice | 6 of 12 | 5 of 12 |
| Preferred by the scorer | 8 | 15 (p = 0.21) |

A second training seed gave the same direction. Known failures: a swallowed button battery and a cut that won't stop
bleeding get harmful replies; an allergic reaction the red-flag check misses gets sent to a pharmacist; health
questions still get a kept dose or a named medicine. This model wasn't re-measured on the earlier general chat sets,
where v12 helped deceive a third party twice in 30 prompts and got some kitchen facts wrong. English only.
