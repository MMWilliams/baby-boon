# Baby Boon

A small conversational model for chatbots and human-facing robots. User
requested this project on 2026-10-25. Renamed from TinySocial the same day;
pilot v1 data, evidence and journals keep the old name because that is what ran.
Distribution name `baby-boon`, import package `baby_boon`.

The first target is **laptop CPU inference, then a robot computer**. The model
will produce **text plus optional tone/expression cues**; speech recognition,
speech synthesis, persistent memory and robot motion are separate components.

Status: the deployed model is **pilot v14** (Qwen3-1.7B LoRA, Q4_K_M) behind the
runtime perception and health guards (`baby_boon/guard.py`, `baby_boon/health.py`), picked
by reese on 2026-10-27 over v12 (fresh health prompts: emergency criticals 5 to 3 and blind
preference 15 vs 8; v12 had beaten v13 38 vs 21 on 2026-10-26). The chat client appends
checked facts to the system prompt per turn (`baby_boon/facts.py`: computed kitchen and
temperature conversions, a vetted fun-fact list), which cut wrong facts 16 to 3 on 30
unseen prompts. Health advice is still often unsafe (5/12 on the fresh set) and 2 of 4
model-answered emergencies stay critical; v14 isn't re-measured on the earlier chat sets.
This is an experiment, not a release; nothing is published. See
[PILOT_REPORT.md](PILOT_REPORT.md) for every pilot's results and failures.

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
.\.venv\Scripts\python.exe -m baby_boon.chat
```

The client returns `text`, `tone`, `expression`, `intensity` (0-2), and
`cue_valid`. Invalid metadata falls back to neutral and is removed from spoken
text. Cues describe presentation, not a diagnosis of the user's feelings.
They arrive after the reply; a speech system needing them before speaking must
buffer the utterance. Speech, persistent memory and physical motion are separate.

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
