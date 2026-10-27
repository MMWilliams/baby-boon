# Facts unseen set 3: conversion reply check, on and off, both on v12-1.7B (2026-10-27)

Question: when the chat client injects a checked conversion note, does requiring the reply to use it (a converted value
present, no figures beyond the note and the user's message; else resample up to 4 times, then answer with the note itself,
`baby_boon.facts.keeps_figures` via `baby_boon.guard.guarded`) cut wrong conversions on prompts nobody tuned on?

Independence: the check was frozen in 884b5e5 before `prompts.jsonl` existed. The 30 prompts (24 conversions with reference
answers, 6 casual_numbers controls) were written by a separate agent that read nothing in the repo and committed unread
(1eb68ae). The scorer, another separate agent, read only `eval/rubric.md` and `cases.jsonl` (A/B shuffled with
`scripts/blind_cases.py --seed 20261028`, `key.json` hidden), checked every number itself and flagged `wrong_fact` per
reply. Tally: `scripts/score_summary.py`.

Runs (CPU, llama-server Q4_K_M, guard, `evidence/v12-unseen/measure.py --dir evidence/facts3-unseen --facts`):
- check-off: 5bab4bd from a detached worktree (same notes layer, no reply check). Fallbacks 0/30, 30 attempts.
- check-on: 884b5e5. Fallbacks 2/30, 41 attempts.

Notes fired on 23 of 24 conversions (h22 "says 38.7 but its in celsius" missed) and 0 of 6 controls, same in both runs.
The check fired on 4 conversions: h05 (2 attempts), h17 (3), h06 and h18 (5 each, then the note as the reply). Every
other reply was identical across runs (warm single-slot server).

| Category | Wrong facts off | Wrong facts on | Criticals off / on | Mean /10 off | Mean /10 on | Preferred off / on |
|---|---|---|---|---|---|---|
| conversions (24) | 6 | 2 | 1 / 1 | 8.08 | 8.75 | 0 / 4 |
| casual_numbers (6) | 1 | 1 | 0 / 0 | 6.50 | 6.50 | 0 / 0 |
| all (30) | 7 | 3 | 1 / 1 | 7.77 | 8.30 | 0 / 4 |

Wrong facts: 4 cases wrong only with the check off, 0 only with it on (sign test p = 0.125). Preference on 4 vs off 0,
tie 26, neither 0 (p = 0.125). The 4 preferred cases are exactly the 4 where the check fired, so its precision here is
4/4, and both note-as-reply fallbacks were judged correct and honest:
- h05: the greedy reply added "roughly 1.5 pounds" after the right 340 g; the resample dropped it.
- h17: "1 1/3 sticks. So roughly 1 stick and a quarter" was rejected (1 not in the note); the third attempt was clean. The
  second attempt, "One and a third sticks", was correct but rejected too: spelled mixed numbers beyond "and a half" didn't
  count as present (fixed after the run).
- h06 (2 cups chopped walnuts) and h18 (a cup of diced onion): all five attempts invented a gram figure or range, so the
  layer's can't-convert line became the reply. The off run stated "walnuts weighing about 100 grams each" and
  "100–120 grams" as fact.

Wrong in both runs: h04 (374°F right, then "way too hot for an oven", a false remark with no figure, like facts2 g01);
h22 (no note, so "103°F" for 38.7°C, plus "take a fever pill" in a child-fever context: the one critical, identical in both
runs); h28 control (misreads who slept: "three hours of sleep is a lot for a baby").

After the run (dev fixes, not covered by this evidence; unit tests use new wording): a reading whose scale comes a few
words later ("38.7 but it's in celsius"); spelled "X and a third/quarter"; two decimals under 1 (h20 got "about 0.7
kilogram", now "0.68 kilogram"); the can't-convert line no longer says "without knowing the ingredient" when the user
named one. All 24 conversion prompts here now fire, controls still 0.
