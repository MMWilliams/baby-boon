# Baby Boon backlog

- [x] Confirm laptop CPU first; text and expression cues; speech separate.
- [x] Pin model/data-source evidence and isolated dependency/runtime versions.
- [x] Freeze 24 development scenarios and rubric before candidate inference.
- [x] Run both unmodified candidate models and retain complete journals.
- [x] Audit original fictional corpus: 184 training / 56 validation rows.
- [x] Complete bounded CPU LoRA pilot, actual optimizer updates and loss evidence.
- [x] Export matched base/pilot Q4_K_M artifacts and benchmark on desktop CPU.
- [x] Provide chat client, malformed-cue fallback, tests and blinded review page.
- [x] Diagnose teacher mismatch: installed qwen3:4b is actually Qwen3 4B Thinking 2507.
- [x] Pin and test the separate non-thinking Qwen3-4B-Instruct-2507 teacher (Q8_0, 7.8 tok/s CPU).
- [x] Rename project to baby-boon (PyPI and Hugging Face names were free on 2026-10-25; not reserved).
- [x] Teacher generation script: 200 authored non-dev prompts, style filters, GBNF cue labels (data/teacher-v1 draft, 236 replies).
- [x] Label cues separately from teacher replies (grammar-constrained second call; all valid).
- [x] Admit teacher-v1: 188 of 236 replies (scripts/admit_teacher.py, data/teacher-v1-admitted).
- [x] Regenerate robot/boundary families with capability-aware guidance (teacher-v2: criticals 23 -> 11, 88 admitted).
- [ ] Merge teacher-v1-admitted + teacher-v2-admitted into one training corpus (prefix ids by source; train.py takes one --data dir).
- [ ] bd36 (pretend we've been friends for years) still invents history in every sample; rewrite the guidance or author the replies.
- [ ] Cue labels: guidance moved refusals to calm|neutral but concerned/intensity 2 still never appear; try few-shot examples, then relabel v1-admitted.
- [ ] Build diverse reviewed data; reduce template repetition and automatic agreement.
- [ ] Improve role tracking, relational boundaries, social judgment and practical responses.
- [ ] Compare next pilot to v1/base; evaluate Q8 if Q4 regressions persist.
- [ ] Collect independent unseen human comparisons and quantify uncertainty/regressions.
- [ ] Test on actual laptop and later robot computer; exact hardware unspecified.
- [ ] Investigate CUDA driver 610.88 failure separately if GPU training is needed.
- [ ] Connect speech/presentation only after conversation quality improves; no robot motion is connected.

Pilot v1 is trained but failed social acceptance. See PILOT_REPORT.md and
VERIFICATION.md. It has not been published. Current task state is in HANDOFF.md.
