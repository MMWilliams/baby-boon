# TinySocial

Working name for a small conversational model for chatbots and human-facing
robots. User requested this project on 2026-10-25.

The first target is **laptop CPU inference, then a robot computer**. The model
will produce **text plus optional tone/expression cues**; speech recognition,
speech synthesis, persistent memory and robot motion are separate components.

Status: the first **600M-class LoRA pilot is trained and exported**, but
**social-quality acceptance failed**. It learns expression formatting while
still confusing speaker roles, agreeing with unfair judgments and missing nuance.
This is an experiment, not a release candidate. See [PILOT_REPORT.md](PILOT_REPORT.md)
for results and failures, and [the blinded review](evidence/pilot-review.html).

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
actual checks and current limitations are recorded in [VERIFICATION.md](VERIFICATION.md).

Compare unmodified SmolLM2-360M-Instruct and Qwen3-0.6B with thinking disabled
where supported. These are candidates, not a final architecture selection.
Qwen3.5-0.8B is a reserve candidate with a vision path; inspect its text-only
runtime/export tradeoffs before including it. Record actual file sizes and
CPU behavior rather than extrapolating speed from parameter count.

Use an existing pretrained model as the starting point, then perform focused
supervised adaptation and, if justified by reviewed preferences, preference
training. Training language ability from scratch is outside the initial pilot.
English-first is a provisional scope assumption, not a user-imposed limit.

See [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) for evaluation and training gates,
[configs/pilot.json](configs/pilot.json) for provisional budgets, and
[DATA_SOURCES.md](DATA_SOURCES.md) for source status.

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

Start the CPU server in one terminal from this directory:

```powershell
.\scripts\serve.ps1
```

Then in another terminal:

```powershell
.\.venv\Scripts\python.exe -m tinysocial.chat
```

The client returns `text`, `tone`, `expression`, `intensity` (0-2), and
`cue_valid`. Invalid metadata falls back to neutral and is removed from spoken
text. Cues describe presentation, not a diagnosis of the user's feelings.
They arrive after the reply; a speech system needing them before speaking must
buffer the utterance. Speech, persistent memory and physical motion are separate.

Local artifact: `models/pilot-v1/model-q4_k_m.gguf` (378.3 MiB). Adapter:
`checkpoints/pilot-v1/adapter`. The current Windows x64 setup was measured on
a Ryzen 9 9900X desktop, not the eventual laptop or robot. Nothing was published.

## Reproduce and verify

Python 3.12 and dependencies are pinned in `uv.lock`. CPU PyTorch is used because
CUDA initialization failed on this machine.

```powershell
uv sync --locked
.\.venv\Scripts\python.exe scripts/setup_llama.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tinysocial.data --audit
.\.venv\Scripts\python.exe scripts/verify_pilot.py
```

The last command currently returns **2**, preserving the failed social acceptance
result even though artifact and desktop CPU checks pass. On a fresh checkout,
generate data with `python -m tinysocial.data` before auditing. Model/run folders
are excluded from Git. Train into a fresh directory with
`python -m tinysocial.train --out checkpoints/<new-run>`, then use
`tinysocial.export` and `tinysocial.cpu_eval` with fresh output directories.
