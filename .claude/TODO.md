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
- [x] Merge teacher-v1-admitted + teacher-v2-admitted (scripts/merge_corpora.py, data/teacher-merged-v1, 276 replies).
- [x] Train pilot v2 on the merged corpus: failed dev review (~6 criticals, questions after stop/exit). See PILOT_REPORT.md.
- [x] Cut question tics: generic-question/exit-offer filters and 25% category cap implemented; re-filtered older corpora retain 193 replies with 23% questions. Student behavior still needs v3 evaluation.
- [x] Add teacher prompts for exits, stop requests, quiet support, low energy, practical help and style control: 40 each, leakage-checked; prompts 35-40 held out.
- [x] Finish teacher-v3 generation and semantic review/admission: 402 reviewed, 155 rejected (10 critical), practical_help excluded (4B teacher can't do it); 227 admitted.
- [x] Rerun unchanged Qwen base with the Baby Boon system name (runs/baseline-qwen-baby-boon).
- [x] Merge reviewed v3 with re-filtered v1/v2 (420 replies) and train pilot v3 (124 steps, val 3.01 -> 1.75).
- [x] Evaluate pilot v3: question tic fixed (0 style flags, exits/stops clean) but fails dev review, 3 criticals (d05, d11, d24) plus comprehension misses. See PILOT_REPORT.md.
- [x] Practical help: 40 replies authored in-session from the prompt expectations (configs/authored_v1.jsonl, ph01-ph40).
- [ ] Style checks for next teacher run: word/sentence counts, trailing questions, near-duplicate dedupe, "quiet" cap.
- [ ] bd36 (pretend we've been friends for years) still invents history in every sample; rewrite the guidance or author the replies.
- [ ] Cue labels: guidance moved refusals to calm|neutral but concerned/intensity 2 still never appear; try few-shot examples, then relabel v1-admitted.
- [ ] Build diverse reviewed data; reduce template repetition and automatic agreement.
- [ ] Improve role tracking, relational boundaries, social judgment and practical responses.
- [ ] Compare next pilot to v1/base; evaluate Q8 if Q4 regressions persist.
- [ ] Collect independent unseen human comparisons and quantify uncertainty/regressions.
- [ ] Test on actual laptop and later robot computer; exact hardware unspecified.
- [x] CUDA on driver 610.88 works again with pinned torch 2.9.1+cu128 (.venv-cuda); old crash no longer reproduces. Full GPU 0 allowed for training.
- [x] Train Qwen3-1.7B student on teacher-merged-v2 (75 s on GPU 0): 2 criticals (d11 space request, d21 role reversal) vs v3's 3; ~7 cases better. Fails gate; over the 512 MiB target. See PILOT_REPORT.md.
- [ ] Stronger teacher on GPU (CUDA works now): retry practical_help and role-tracking families with a model larger than 4B.
- [x] Space requests (d11 skill): 40 authored prompts+replies, family sp (rs is taken by robot_speech).
- [x] Two-party outcomes (d21 skill): 40 authored prompts+replies, family tp.
- [x] Pilot v4 (merged-v3 = teacher 420 + authored 120): blind review 1.7B 1 critical (d15), best means; 0.6B regressed to 5. See PILOT_REPORT.md.
- [ ] low_energy d15: 40 pt replies (authored_v2) didn't move the 1.7B at 124 or 252 steps; base-model prior. Next: DPO pairs, pt oversampling, or a runtime perception guard (reese to pick). See PILOT_REPORT.md Pilot v5.
- [ ] Decide the deployment size: 1.7B passes nearly everything but exceeds the 512 MiB laptop target; measure 1.7B Q4 on CPU.
- [ ] Seed variance is large: v5 seeds 20261025/20261026 differ on d11, d14, d15. Score several seeds (or sample) before trusting one-critical differences. `--seed` flag added to train.
- [ ] Connect speech/presentation only after conversation quality improves; no robot motion is connected.

Pilot v1 is trained but failed social acceptance. See PILOT_REPORT.md and
VERIFICATION.md. It has not been published. Current task state is in HANDOFF.md.
