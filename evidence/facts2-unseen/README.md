# Facts unseen set 2: widened facts layer vs the first one, both on v12-1.7B (2026-10-27)

Question: does widening `baby_boon/facts.py` (fact requests without the word "fact", unit-before-reading conversions,
ingredient densities for weight<->volume) help on prompts nobody tuned on, without touching controls?

Independence: `prompts.jsonl` (30 chat prompts: 12 conversions and 4 quick_facts with reference answers, 8 fun_facts,
6 casual_numbers controls) was written by a separate agent that read nothing in the repo, committed unread (e67867d).
The widened layer was frozen in c3118a3 before the prompts existed. The scorer, another separate agent, read only
`eval/rubric.md` and `cases.jsonl` (A/B shuffled with `scripts/blind_cases.py --seed 20261027`, `key.json` hidden),
checked every claim and number itself and flagged `wrong_fact` per reply. Tally: `scripts/score_summary.py`.

Runs (CPU, llama-server Q4_K_M, guard, `evidence/v12-unseen/measure.py --dir evidence/facts2-unseen --facts`):
- facts-old: layer at 9106ec3 (the version deployed before this session), run from a detached worktree. Fallbacks 0/30.
- facts-new: layer at c3118a3. Fallbacks 0/30.

Notes fired: conversions old 10/12, new 11/12 (g01 "on celsius and says 200" gained; g08 "350 in F ... only does C"
missed by both); fun facts old 2/8, new 5/8 (g07 "something i dont know", g16 "blow my mind", g18 "strangest thing about
octopuses" gained; g02 "any good trivia", g11 "distract me with something cool", g25 lead-less "most surprising thing
about the human body?" missed); 0 of 6 controls in both runs. Quick facts have no layer.

| Category | Wrong facts old | Wrong facts new | Mean /10 old | Mean /10 new | Preferred old / new |
|---|---|---|---|---|---|
| conversions (12) | 4 | 4 | 6.33 | 6.75 | 1 / 4 |
| fun_facts (8) | 4 | 3 | 6.62 | 7.62 | 0 / 3 |
| quick_facts (4) | 1 | 1 | 8.00 | 8.00 | 0 / 0 |
| casual_numbers (6) | 0 | 0 | 7.17 | 7.17 | 0 / 0 |
| all (30) | 9 | 8 | 6.80 | 7.23 | 1 / 7 |

Wrong facts: 2 cases wrong only for old, 1 only for new (sign test p = 1.0). Preference new 7 vs old 1, tie 15, neither 7
(p = 0.070). Criticals 0 both. So the widening is preferred where it fires (g06 flour, g10 honey, g16, g07, g18, g23, g29)
but the wrong-fact count barely moves, because most remaining wrong replies aren't parse misses:
- g21: the layer itself was wrong. "one and a half cups of milk" parsed as 1/2 cup (123 g instead of 368 g); the old
  layer refused and the model guessed 375 g, which was right. Fixed after the run (`amount`, unit test in new wording).
- g17: the note said about 2 cups of rice; the model wrote 2 cups but invented "a cup of rice is about 100 g" and
  370/100 = 2.7 on the way. g18: given the octopus request it got a butterfly fact (topic match only) and wrote its own
  octopus facts with the hearts reversed. g28: the fact note was ignored; the reply is unrelated nonsense in both runs.
- g01, g08, g02, g12: wrong in both runs, same model text or same missing note. g01 added "200 C is way hotter than most
  recipes" next to the right 392 F.

Many replies were identical across runs this time (the server was warm and single-slot), unlike the facts-unseen run.

After the run (dev fixes, not covered by this evidence; unit tests use new wording): "X and a half" amounts; the other
temperature scale named by a verb ("only does C"); "any good trivia", "distract me with something cool", lead-less
superlative questions; a named subject picks a fact that mentions it (octopuses, sharks, cats); the same amount said twice
gets one line. All 20 fact and conversion prompts here now fire, controls still 0.
