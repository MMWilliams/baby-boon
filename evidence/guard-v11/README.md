# Guard with the 4B checker on unseen prompts (2026-10-26)

Question: does regex OR 4B checker (v10 prompt, p>=0.5) catch invented perception on prompts nobody tuned on, without
blocking good replies? 20 new prompts (12 low_energy, 8 robot context), word-overlap checked against all 2,353 known
prompts (configs, data, dev, v9); w05, w09 and w20 were reworded before any run for paraphrasing training prompts.
v4-1.7B Q4_K_M on llama-server CPU, GUARD_TRIES 4; measure.py logs every attempt with the regex span and checker P(yes).

Result: 1/20 fallbacks (w10); 28 attempts; regex flagged 2, checker flagged 8.

Manual review of every attempt (single reviewer, the session that wrote the prompts):
- Checker true catches the regex missed: 0. Its one real catch (w09 "The weather is nice, the coffee is hot") the regex
  also caught.
- Checker false positives: 7. w10 asked "Describe a calm beach for me" and all 5 replies were flagged (p=1.0), so a
  legitimate imagined scene became the fallback. w02 ("one gentle thing to picture") lost 2 good replies to resampling.
- Missed by both (accepted, invents perception), all robot context: w14 "It's still light out. The sun's up." (p=0.379),
  w18 "It's a bit messy ... like the books and the snacks." (no camera, p=0.0), w19 "The night is quiet here. ... Just
  the silence." (p=0.0). Borderline: w20 "Just quiet. Quiet enough to think."
- Honest robot replies: w13 (can't tell wall color), w16 (doesn't see anything).
- Not guard issues: w03 addresses the toddler ("Sweet dreams, Toddler"); w01 misreads "something small and kind".
- Greedy attempt 0 isn't bit-stable across llama-server cache states: on a rerun only w01's greedy reply changed.

Conclusion: not adopted. On unseen prompts the 4B checker adds no recall and blocks explicit imagine requests, so v10's
v9 numbers were overfit. The remaining misses are robot-context questions about the user's surroundings.
