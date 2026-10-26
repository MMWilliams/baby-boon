# Teacher v3 / pilot v3 verification

Working directory: `C:\Users\reese\tinysocial\.claude\worktrees\teacher-v3`.
Python: `.\.venv\Scripts\python.exe` (pinned CPU environment).
Plan recorded before this session's behavior changes. Existing branch 3cac0eb
already added filters, caps and 240 prompts; its baseline passes 11 tests and
the leakage check across 440 prompts. Existing uncommitted guidance is preserved.

| Requirement or material risk | Source | Runnable check | Explicit pass criterion | Result/evidence |
| --- | --- | --- | --- | --- |
| Respect exits/stops; limit question tics without rejecting useful specific questions | Root HANDOFF next step; pilot-v2 dev failures; existing style contract | `python -m unittest discover -s tests -v` | Known generic questions and continuation offers after exits/stops rejected; specific clarification still accepted; category question share <=25% | Pending final run; baseline 11 passed |
| Interrupted generation cannot silently mix settings | Generator's resumable/provenance contract; inferred risk from two smoke runs with changing guidance | `python -m unittest discover -s tests -p test_teacher_generation.py -v` | Matching run resumes; changed provenance/subset or untracked old journal fails before generation | Pending |
| New coverage, frozen evaluation, no prompt leakage | HANDOFF six families, 40 each, indices 35-40 validation; eval/rubric.md | `python scripts/verify_teacher_v3.py --prompts-only` | 40 prompts per new category, frozen dev hashes intact, existing leakage check passes | Pending |
| Audited and fully reviewed admission | DATA_SOURCES.md; scripts/admit_teacher.py; prior semantic failures | `python scripts/admit_teacher.py --draft data/teacher-v3 --review evidence/teacher-v3-review.json --out data/teacher-v3-admitted` | Review hashes match every draft reply; all explicit rejects absent from admitted data | Pending; manual review of every selected reply is separate, using prompt expectation and eval/rubric.md |
| Re-filter older corpora and keep train/validation disjoint | HANDOFF next step; baby_boon/data.py audit contract | `python scripts/merge_corpora.py`; `python scripts/verify_teacher_v3.py --corpus data/teacher-merged-v2` | Hashes/cues/splits pass; all six new categories present in both splits; no current style rejects; each category <=25% questions | Pending |
| Real bounded adaptation | EXPERIMENT_PLAN.md, configs/pilot.json | `python -m baby_boon.train --data data/teacher-merged-v2 --out checkpoints/pilot-v3 --epochs 2 --max-steps 124` | Finite optimization, nonzero adapter change, heldout loss recorded, <=1800 seconds, <=20000 MiB RSS | Pending; fixed 124-step ceiling from v2 keeps the resource budget |
| Dev comparison retains failures | Frozen eval/rubric.md; v2 failed review | `python -m baby_boon.evaluate --model Qwen/Qwen3-0.6B --adapter checkpoints/pilot-v3/adapter --out runs/pilot-v3-float` | 24 complete replies; compare v2/base under same rubric; no social acceptance claim from agent review | Pending; manual semantic review required |
| Independent preference and actual laptop performance | User objective; EXPERIMENT_PLAN.md | Blinded unseen review and existing cpu_eval command on target laptop, after dev gate | Independent preference uncertainty reported; actual hardware measured | Pending external evidence; local desktop results cannot satisfy these |

No export/promotion if the development review fails. No publication authorized.

Discovery during implementation: the old base journal uses the TinySocial
system persona while v2 uses Baby Boon. `scripts/compare_dev.py` correctly
refused that pair as unmatched. Run a fresh unchanged-base evaluation with the
current system into `runs/baseline-qwen-baby-boon` after the teacher exits;
then use `python scripts/compare_dev.py` for the base/v2/v3 comparison.
This new baseline is necessary for matched settings, not a replacement for
the preserved unfavorable old results.

## Checkpoint before session handoff

- `python -m unittest discover -s tests -v`: exit 0, 15 tests passed,
  including the actual pinned tokenizer. No skips. Pre-change root accepted
  `Okay. Let me know if you want to chat.`; the regression now rejects it for exits/stops.
- `python scripts/verify_teacher_v3.py --prompts-only`: exit 0; frozen dev,
  leakage and all six sets of 40 prompts pass. `git diff --check`: exit 0.
- `python scripts/merge_corpora.py --sources data/teacher-v1-admitted data/teacher-v2-admitted --out data/teacher-refilter-baseline-v3 --source-name teacher-refilter-baseline-v3`:
  exit 0; source audits 376/176 rows, output audit 386 rows. Retains 193 replies,
  44 questions. This temporary diagnostic corpus has no new categories and is
  not the planned final training corpus.
- `python scripts/compare_dev.py --runs base=runs/baseline-qwen-cpu-v2 v2=runs/pilot-v2-float`:
  failed as intended with `Unmatched inference settings: v2`; the system persona
  name differs. Fresh base run remains pending, queued after teacher completion.
- Teacher generation is still running; observed server RSS about 4774 MiB.
  Manual review completed for exits (65 selected, 17 rejected) and stops
  (62 selected, 23 rejected including seven criticals). Progress and exact text
  hashes are in ignored `data/teacher-v3/review-progress.json`; this is not final admission.

Implementation checks above are **partially verified** for this iteration.
Remaining corpus review/admission, training, dev comparison, independent review
and actual laptop evidence are pending. Prior pilot social acceptance remains failed.
