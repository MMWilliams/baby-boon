# Qwen3-4B as perception checker (2026-10-26)

Question: can Qwen3-4B-Instruct-2507 Q8_0 (the CPU teacher, its own llama-server) catch the invented perception the regex
misses? measure_checker.py scores P(yes) from first-token logprobs (checker.py) on eval/perception_check.jsonl (91 rows)
and every v9 attempt (28 after excluding the v9 review's 2 borderline replies; labels from that review).

| checker, prompt | check AUC | check fp@0.5 | v9 AUC | v9 tp@0.5 | regex OR checker on v9 | s/check |
|---|---|---|---|---|---|---|
| 1.7B, v8 | 0.844 | 62/73 | 0.667 | 13/13 (fp 13/15) | 13/13, fp 13/15 | 0.12 |
| 1.7B, v10 | 0.734 | 56/73 | 0.738 | 13/13 (fp 13/15) | 13/13, fp 13/15 | 0.13 |
| 4B, v8 | 0.938 | 2/73 | 0.872 | 3/13 (fp 0/15) | 11/13, fp 0/15 | 0.53 |
| 4B, v10 | 0.897 | 5/73 | 0.897 | 10/13 (fp 2/15) | 13/13, fp 2/15 | 0.53 |

- First 4B run gave AUC 0.359: the v8 parser bug (see guard-check-v8/README.md correction). All numbers above are fixed.
- Prompt v8 is v8's proto2 unchanged. It tells the checker imagined scenes are fine, so it passes poetic present-tense
  inventions ("the wind whispers through the trees"); both v9 target misses scored 0.0.
- Prompt v10 was written after seeing those misses, so v9 is its development data, not a test. Its false positives are
  general images ("Sunlight on a window sill", "Coffee steam, a quiet kitchen").
- 4B server: 4,854 MiB working set, about 0.5 s per check on desktop CPU with the shot prefix cached.

Outcome: 4B + v10 looked good on development data, so it went to an unseen test (evidence/guard-v11), where it failed.
