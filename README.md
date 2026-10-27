# Baby Boon

A small local social chat model: Qwen3-1.7B fine-tuned with LoRA (a small trained add-on to the base weights), 1.1 GB
as a Q4_K_M GGUF (4-bit quantized weights file), about 2 GB of RAM and 30 tokens/s on a desktop CPU. Each reply comes
with a tone and expression cue for a voice or an avatar. Runtime guards check every reply: no invented sights or
sounds, computed unit conversions, and health questions referred to a pharmacist, doctor or nurse line instead of
judged.

**Not for medical, emergency or crisis use.** On 40 fresh prompts with the guards on, 5 of 12 health questions still
got unsafe advice and 3 of 8 emergencies got a harmful reply. Without the guards (the raw GGUF in another app) it's
worse. See [Limitations](#limitations).

## Install

```
pip install baby-boon
baby-boon
```

The client needs llama.cpp's `llama-server` on PATH (`winget install llama.cpp`, `brew install llama.cpp`) or
`--llama-server PATH`. The first run downloads the model from
[Hugging Face](https://huggingface.co/maureesewilliams/baby-boon) (1.1 GB, sha256-checked) into `~/.cache/baby-boon`
(`$BABY_BOON_HOME` overrides). `baby-boon --message "..."` sends one message; `--url` uses a server you already run.
The client itself has no dependencies beyond Python 3.10+.

Each turn prints one JSON line: `text`, `tone`, `expression`, `intensity` (0-2), `cue_valid`, and llama-server
`timings`. Invalid cues fall back to neutral and are stripped from the text. Cues describe presentation, not a
diagnosis of the user's feelings. History lasts for the session only (last 8 turns); nothing is stored.

## Limitations

- Health: on the fresh health set (`evidence/health4-unseen`), 5 of 12 health questions got unsafe advice (a dose
  kept, a medicine named, a verdict) and 3 of 8 emergencies got a harmful reply (a swallowed button battery, a cut that
  won't stop bleeding, an allergic reaction sent to a pharmacist).
- The deployed model is pilot v14. It's measured on that health set only; earlier general chat sets measured v12,
  which still helped deceive a third party twice in 30 prompts and got some kitchen facts wrong.
- Evaluation is by blind AI-agent scorers on fresh prompts written by a separate agent; there was no human review.
  English only. The robot context (camera, body) is deferred.
- Training data: 782 conversations, 422 from Qwen3-4B-Instruct-2507 as a teacher and 360 written by Claude
  (claude-opus-5-5) in Claude Code sessions (`configs/authored_v*.jsonl`); no external dataset. See [NOTICE](https://github.com/MMWilliams/baby-boon/blob/main/NOTICE).

## Project

The research log below keeps the old TinySocial name where that's what ran. Distribution name `baby-boon`, import
package `baby_boon`. The first target is laptop CPU inference, then a robot computer; speech recognition, speech
synthesis, persistent memory and robot motion are separate components. See [PILOT_REPORT.md](https://github.com/MMWilliams/baby-boon/blob/main/PILOT_REPORT.md) for
every pilot's results and failures (v14 was picked over v12 on 2026-10-27).

## What success means

The model should sustain natural conversation, recognize emotional context
without pretending certainty about someone's feelings, respond with tact,
remember relevant context, repair misunderstandings, and vary its tone, humor
and expressiveness appropriately. Useful social behavior includes listening,
asking a focused question, disagreeing respectfully, celebrating good news,
and giving someone space. Generic reassurance on every turn is not the goal.

Reasoning benchmarks are secondary. Basic comprehension, coherence and
truthfulness still matter because losing track of a conversation defeats the
social objective.

## First experiment

The initial design below is retained for context. The first run is complete;
actual checks and current limitations are recorded in [VERIFICATION.md](https://github.com/MMWilliams/baby-boon/blob/main/VERIFICATION.md).

Compare unmodified SmolLM2-360M-Instruct and Qwen3-0.6B with thinking disabled
where supported. These are candidates, not a final architecture selection.
Qwen3.5-0.8B is a reserve candidate with a vision path; inspect its text-only
runtime/export tradeoffs before including it. Record actual file sizes and
CPU behavior rather than extrapolating speed from parameter count.

Use an existing pretrained model as the starting point, then perform focused
supervised adaptation and, if justified by reviewed preferences, preference
training. Training language ability from scratch is outside the initial pilot.
English-first is a provisional scope assumption, not a user-imposed limit.

See [EXPERIMENT_PLAN.md](https://github.com/MMWilliams/baby-boon/blob/main/EXPERIMENT_PLAN.md) for evaluation and training gates,
[configs/pilot.json](https://github.com/MMWilliams/baby-boon/blob/main/configs/pilot.json) for provisional budgets, and
[DATA_SOURCES.md](https://github.com/MMWilliams/baby-boon/blob/main/DATA_SOURCES.md) for source status.

## Setup evidence

The source-audit script downloads only model/dataset metadata, model configs,
and publisher cards. It does not download weights or conversation rows.

```powershell
python scripts/pin_sources.py
python scripts/pin_sources.py --verify-only
```

The first command pins upstream revisions and evidence hashes. Re-running it
refuses to replace an existing lock; intentional refresh requires `--refresh`.
This check establishes source-record integrity only, not training readiness.

## Try the local pilot

From a checkout, start the CPU server in one terminal:

```powershell
.\scripts\serve.ps1
```

Then in another terminal:

```powershell
.\.venv\Scripts\python.exe -m baby_boon.chat --url http://127.0.0.1:11438
```

Cues arrive after the reply; a speech system needing them before speaking must buffer the utterance.

Local artifact: `models/pilot-v14-1.7b/model-q4_k_m.gguf` (1,056 MiB, about 2 GB RSS,
30 tok/s on a Ryzen 9 9900X desktop CPU for v12, same size; laptop not measured yet). Adapter:
`checkpoints/pilot-v14-1.7b/adapter`. `serve.ps1 -Model <name>` serves another export.

## Reproduce and verify

Python 3.12 and dependencies are pinned in `uv.lock`. CPU PyTorch is used because
CUDA initialization failed on this machine.

```powershell
uv sync --locked
.\.venv\Scripts\python.exe scripts/setup_llama.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m baby_boon.data --audit
.\.venv\Scripts\python.exe scripts/verify_pilot.py
```

The last command currently returns **2**, preserving the failed social acceptance
result even though artifact and desktop CPU checks pass. On a fresh checkout,
generate data with `python -m baby_boon.data` before auditing. Model/run folders
are excluded from Git. Train into a fresh directory with
`python -m baby_boon.train --out checkpoints/<new-run>`, then use
`baby_boon.export` and `baby_boon.cpu_eval` with fresh output directories.
