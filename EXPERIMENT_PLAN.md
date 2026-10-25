# Baby Boon initial experiment and verification plan

User criteria: very small and fast; strong conversation/human interaction;
social and emotional responsiveness; expressive; chatbot and humanoid use.
Confirmed 2026-10-25: laptop CPU first, then robot computer; text plus expression
cues; speech separate. No publication or use of private personal data requested.

## Compare before training

1. Pin candidate revisions, license evidence and dependencies. Inspect current
   model docs for supported chat templates and CPU export runtimes.
2. Write a development scenario suite before any model outputs are inspected.
   These are authored development fixtures, not an independent human benchmark.
3. Run both unmodified candidates with identical contextual scenarios and
   generation budgets. Disable reasoning traces where the model supports it.
4. Collect full responses, truncation/failure counts, prompt sizes, first-token
   latency, decode throughput, cold load time, model bytes and full process RAM.
5. Compare a tiny supervised pilot against its unchanged base. Use bounded
   training on GPU 0, then assess the quantized CPU export, not just the GPU
   checkpoint. Preserve unfavorable results and rejected candidates.

## What to evaluate

Use diverse multi-turn dialogues and paired context changes. Include:

- Casual banter, shared interests, playfulness and good news.
- Frustration, embarrassment, uncertainty and disappointment, with appropriate
  restraint; do not force a therapeutic tone onto ordinary conversation.
- Indirect requests, politeness, teasing and ambiguous cues; ask instead of
  confidently inventing another person's intent.
- Topic continuity, user corrections, remembered preferences and graceful
  repair after the assistant misunderstands.
- Respectful disagreement and truthful uncertainty, including when agreement
  would be socially easy but factually wrong.
- Adjustable verbosity, warmth, energy and humor without becoming repetitive.
- Robot interaction with explicit observed state: interrupted speech, a missed
  utterance, turn handover, greeting a returning person and respecting a request
  for space. Do not pretend text-only input contains unseen facial/vocal cues.

Blind human preference comparisons are required for a claim of improved social
quality. Automated checks may detect schema errors, lost facts, repetition and
task-specific failures, but cannot certify empathy or naturalness. A model judge
can assist triage; it is not a substitute for independent human assessment.

## Expression interface

Start with plain conversational text for baseline quality. Compare a compact
structured mode containing `text`, `tone`, `expression` and `intensity` only
after the baseline. Cue vocabulary and exact serialization remain to be chosen
from measured token/latency overhead. Include a neutral/no-expression option.

Cues describe desired presentation. A separate validated application maps them
to a voice or animation. This pilot does not connect the model to joint commands
or physical robot actuation. Persistent memory belongs outside the model and
must distinguish stated facts from uncertain inferences.

## Verification matrix

Commands marked **planned** do not exist yet and must be implemented before the
corresponding stage is called complete. Establish detailed numerical social
acceptance criteria with independent reviewers before the final comparison.

Implementation update: [VERIFICATION.md](VERIFICATION.md) maps these original
planned commands to the actual pilot modules and records execution. Training
uses the CPU fallback after native and WSL CUDA initialization failed. The
original intended checks below remain visible; GPU availability is not claimed.

| Requirement or material risk | Source | Runnable check | Explicit pass criterion | Status |
| --- | --- | --- | --- | --- |
| Reproducible source intake | Model/dataset publisher revisions; research integrity | `python scripts/pin_sources.py`; `python scripts/pin_sources.py --verify-only` | All recorded local evidence hashes match; exact source revision and declared license captured | Passed 2026-10-25: 7 source records, 10 evidence files; this does not establish dataset admission or training readiness |
| Training data rights and provenance | Intended distributable chatbot/robot model; original-source terms | Planned: `python -m baby_boon.data.audit --manifest data/manifest.json` plus source review | Every row attributable to an admitted source; no NC/unknown-rights source admitted; private user chats excluded | Pending; no rows admitted |
| No family/tree leakage | Social generalization and evaluation integrity | Planned: `python -m baby_boon.data.verify_splits` | No source conversation, duplicate cluster or generator family spans train/dev/final; hashes frozen before training | Pending |
| Real pre-training baseline | User's small/fast/social objective | Planned: `python -m baby_boon.evaluate --config configs/baseline.json` | Both exact base checkpoints produce complete journals under matching prompts; every failure retained | Pending |
| Assistant-only training and valid cues | Avoid teaching prompt echo; proposed expression interface | Planned: `python -m baby_boon.train --config configs/smoke.json` and masking/schema tests | Real optimizer step; finite gradients; user/padding tokens excluded from loss; boundary and malformed-cue cases checked | Pending |
| Resource limits | Conservative prior local-model resource policy | Planned: `python -m baby_boon.preflight`; monitored pilot run | GPU 0 only <=16000 MiB process allocation; GPU 1 unused; host <=20000 MiB; no paid calls or disturbance of unrelated jobs | Pending |
| Social quality improvement | User's primary objective | Planned: blinded human baseline/pilot comparisons on independent scenarios | Preference improvement with uncertainty reported, plus no material regressions in continuity, honesty and appropriate response style; thresholds set before review | Pending |
| Actual laptop performance | Confirmed CPU-first deployment | Planned: `python -m baby_boon.benchmark --runtime llama.cpp --threads <fixed> --device-report <file>` | Report warm/cold latency, throughput, process RAM, context and artifacts; compare with provisional targets; laptop test required for laptop claims | Pending |
| Quantization preserves usable behavior | Deployable tiny checkpoint | Planned: same held-out review and schema checks on quantized export | Report paired float/export quality and speed; do not infer behavior from float checkpoint alone | Pending |

## Milestones

Baseline and corpus design -> reviewed small SFT pilot -> blind evaluation ->
quantized CPU comparison -> preference training if justified -> application
integration. Do not describe a loss decrease or a handful of pleasant examples
as evidence that the model is emotionally intelligent. No checkpoint promotion
until the relevant checks pass.
