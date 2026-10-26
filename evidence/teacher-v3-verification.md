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
