# TinySocial

Working name for a small conversational model for chatbots and human-facing
robots. User requested this project on 2026-10-25.

The first target is **laptop CPU inference, then a robot computer**. The model
will produce **text plus optional tone/expression cues**; speech recognition,
speech synthesis, persistent memory and robot motion are separate components.

Status: project definition and source review started. **No new checkpoint has
been trained, and no social-quality or latency claim has been established.**

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
