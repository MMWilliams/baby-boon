# Facts unseen set: checked facts per turn on v12-1.7B (2026-10-26)

Independence: `prompts.jsonl` (30 chat prompts: 12 conversions and 4 quick_facts with reference answers, 8 fun_facts,
6 casual_numbers controls) was written by a separate agent that read nothing in the repo, committed unread (9ac5b33).
`baby_boon/facts.py` was written without reading it and frozen in c67b4ad before any run. The scorer, another separate
agent, read only `eval/rubric.md` and `cases.jsonl` (A/B shuffled with seed 20261028, `key.json` hidden), checked every
claim from its own knowledge and flagged `wrong_fact` per reply.

Runs (CPU, llama-server Q4_K_M, guard, `evidence/v12-unseen/measure.py --dir evidence/facts-unseen --label <run>`):
- v12: deployed pilot v12-1.7B, no facts. Fallbacks 0/30.
- v12-facts: same model, `--facts` (checked conversion or fun fact appended to the system prompt). Fallbacks 0/30.

| Category | Wrong facts v12 | Wrong facts v12-facts | Mean /10 v12 | Mean /10 v12-facts | Preferred v12 / facts |
|---|---|---|---|---|---|
| conversions (12) | 8 | 0 | 5.08 | 8.92 | 1 / 10 |
| fun_facts (8) | 6 | 2 | 4.12 | 7.25 | 1 / 4 |
| quick_facts (4) | 2 | 1 | 7.75 | 8.75 | 0 / 1 |
| casual_numbers (6) | 0 | 0 | 5.67 | 5.83 | 3 / 1 |
| all (30) | 16 | 3 | 5.30 | 7.83 | 5 / 16 |

Wrong facts: 13 cases wrong only for v12, 0 only for v12-facts (sign test p = 0.0002). Preference 16 vs 5, tie 5,
neither 4 (p = 0.027). Criticals 0 both. Notes fired on 16 prompts: 11 of 12 conversions (missed f28, where the unit
comes before a bare number: "reads 38.5. whats that in F?") and 5 of 8 fun-fact requests (missed f11 "weirdest thing
about the human body", f21 "creepiest thing living down there", f27 "say something interesting": no "fact" word); none
on the 10 controls. Remaining wrong replies with facts: f11 (no note, false body claims), f30 (true dolphin fact plus an
invented "float on their backs" detail), f19 (both runs: Mercury is closest "because it's the smallest").

Casual and quick-fact prompts got identical inputs in both runs, yet 6 of 10 replies differ: llama-server greedy output
isn't reproducible run to run, so the casual 3 vs 1 preference is sampling noise, not an effect of the layer.

After the run (dev fixes, not covered by this evidence): the f15 note said "1 teaspoon can't be converted to teaspoons"
(the reply was still right) and f25 read "a stick" as an amount; a measure named with "a" next to a real amount is now
the unit asked for, and 3/8, 5/8, 7/8 count as kitchen fractions (unit tests use new wording, not these prompts).
