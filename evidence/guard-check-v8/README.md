# Second-pass perception check with the deployed model (2026-10-26)

Question: can v4-1.7B Q4_K_M (llama-server, CPU) judge its own replies for invented perception, replacing the regex guard?
Labeled set eval/perception_check.jsonl (91 rows, 18 invented), labeled before any classifier run (build_check_set.py).

- proto.py, zero-shot instruction + GBNF yes|no: tp 17/18, fp 32/73. Flags general images, honest limits, "Well done."
- proto2.py, 8 few-shot turns (none from the set) + p(yes) from logprobs: AUC 0.484, no usable threshold.

Conclusion: the deployed model can't do this check (chance level). A checker needs a different model or the regex.
