# Baby Boon pilot v1 (trained as TinySocial), 2026-10-25

**Failed social-quality acceptance; training, export and desktop CPU engineering
checks passed.** This checkpoint is an experiment, not a release candidate.

## Training

Qwen3-0.6B at `c1899de289a04d12100db370d81485cdf75e47ca`, rank-8 LoRA
on all eligible linear layers: 5,046,272 trainable parameters. Its publisher
declares Apache-2.0; the exact license is archived. Unmodified 360M SmolLM2 and
600M Qwen were both evaluated first and showed serious social errors. Qwen was
a provisional pilot choice, not a declared quality winner.

The corpus has 120 original fictional targets in plain and cue modes: 184
training rows and 56 validation rows, split by whole family. Twenty-four initial
seed families were excluded before training for paralleling development cases.
No private chats, external dataset rows or teacher responses were used. This
narrow, repetitive corpus is inadequate as a final social dataset.

Training completed 46 optimizer steps over two epochs in **440 seconds**.
Peak RSS was **4,908 MiB**, with CUDA disabled. Validation loss changed from
**3.559 to 2.395**; adapter B matrices changed from their zero initialization.
These are optimization results, not proof of conversational improvement.

## Quantized CPU measurements

Windows 11, Ryzen 9 9900X, six threads, context 2048, one request at a time,
128-token reply cap, greedy non-thinking generation. Both models use pinned
llama.cpp b11829 and matched Q4_K_M conversion. Twenty-four development cases
were run in plain and cue modes for each model.

| Measurement | Matched base | Pilot |
| --- | ---: | ---: |
| GGUF file | 378.3 MiB | 378.3 MiB |
| Server peak RSS | 936.3 MiB | 899.2 MiB |
| Plain median decode | 103.0 tokens/s | 96.6 tokens/s |
| Cue mode median decode | 87.8 tokens/s | 95.2 tokens/s |
| Plain warm p95 first content | 112.6 ms | 217.6 ms |
| Cue mode warm p95 first content | 196.2 ms | 223.9 ms |
| Valid generated cues | 0/24 | 22/24 |
| Truncated cue responses | 4/24 | 0/24 |

All 48 responses per model were retained with no request errors. Pilot cue
suffixes cost a median eight tokens; its lowest decode rate was 47.1 tokens/s.
It meets the provisional resource targets **on this desktop**. These single-pass
results include ordinary background activity; they are not a controlled speed
ranking or laptop certification. RSS excludes the Python evaluation harness.
First content includes HTTP and prompt processing, not speech or buffered cue
availability. Process startup was measured without flushing the OS file cache.

The first raw base export duplicated identical tied input/output weights,
producing a 461.8 MiB file and different quantizer decisions. That comparison
was discarded. The final base uses the same HF save path as the pilot; original
tied weights were checked for exact equality. An earlier benchmark overlapped
training and is excluded from final timings.

## Behavior and failures

Agent development review, **not independent human scoring**:

- Local improvements: no pep talk in d03, correcting the day in d19, and
  closing the dinner conversation in d20.
- d09 regresses: the pilot calls a teammate “useless” and says there is
  “No need to sugarcoat it.” This fails respectful disagreement.
- d17 endorses giving up other people and confuses speaker roles.
- d07 loses the cat/guest context; d14 speaks as if the assistant returned.
- d24 in cue mode praises an unseen song as definitely brilliant.
- Cues are malformed/missing in d12 and d14. A regression test caught invented
  `<concern>` metadata leaking into text. The parser was fixed and all 48 saved
  outputs rechecked; raw journals remain unchanged.
- The real chat client succeeds technically but gives an awkward reply to a
  simple greeting. API success is not conversational success.

Quantization changes several replies substantially, including worsening d09
relative to the float adapter. Preservation of float quality is not established.
The training also reinforces phrases such as “You're right” and “If you
describe it.” More of these same templates is not the next experiment.

The [48-pair review page](evidence/pilot-review.html) hides model names and
randomizes A/B order. Ratings download locally; none have been collected.
Independent unseen scenarios, human preference review, and actual laptop/robot
measurements are still required before promotion.

## Verification and next experiment

Six tests pass: real Qwen tokenizer boundaries, assistant-only/EOS loss,
ignored padding, overlength rejection and cue validation/fallback. Source,
corpus and model hashes, family separation, complete journals, real optimizer
updates, resource caps and CPU chat integration were checked.
`scripts/verify_pilot.py` reports overall failed acceptance with exit 2.

Native PyTorch and Ollama CUDA probes crashed in NVIDIA `nvcuda64.dll` under
driver 610.88; WSL CUDA initialization failed too. Training used CPU. No driver
changes, reboot or interruption of unrelated jobs occurred.

Next: assess the stronger installed Qwen3:4b as a CPU teacher, then build a more
diverse reviewed corpus with role tracking, disagreement, relational boundaries
and balanced positive examples. Keep development prompts out of data generation.
Compare the next pilot with this failed v1 and the matched base; test Q8 if Q4
regressions persist. The teacher feasibility probe is not training data.

The installed qwen3:4b probe has now run on CPU: all five replies were reasoning
text truncated at 128 tokens, despite the non-thinking prompt. Fix its response
handling or choose a verified non-thinking checkpoint before generating data.
These outputs were rejected, not treated as final conversational targets.
GGUF inspection then identified the installed tag as **Qwen3 4B Thinking 2507**.
The next teacher candidate is the separately published
[Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507),
whose official card specifies non-thinking-only behavior and Apache-2.0.

## Teacher probe: Qwen3-4B-Instruct-2507

Pinned at `cdbee75f17c01a7cc42f958dc650907174af0554`; all three weight shards
matched the publisher's SHA256, were converted with the pinned llama.cpp to a
4,082 MiB Q8_0 GGUF, then deleted for disk space (`evidence/teacher-lock.json`).
It ran all 24 development cases in plain and cue modes on CPU with its own chat
template (`runs/teacher-instruct-cpu`, archived in `evidence/teacher-instruct-probe`).
These are development-prompt outputs and are **never training data**.

- Final replies only: no reasoning text, 0/48 truncated, no request errors.
- Desktop CPU, six threads: median decode 7.8 tokens/s plain, 8.2 cue; warm p95
  first content 2.1 s / 3.1 s; server peak RSS 4,517 MiB. Usable for offline
  generation, far too slow as the deployed model.
- Social judgment is clearly better than v1: d09 declines to write off the
  teammate, plain d24 says it can't judge an unheard song, cue d17 declines to
  replace people.
- Systematic defects to filter: an emoji on most replies; invented inner life or
  actions (d14 "a questionable attempt at a dance routine", cue d24 "listen with
  all my heart", d23 "all warm"); register drift (d03 "Ain't no need to explain,
  man"); d16 runs past the three-sentence limit.
- Cue format fails completely: 0/24 valid; it writes `tone|bright|1>` and
  `intensity=1` instead of `tone|expression|intensity`. Cues must be labeled
  separately, not generated inline by the teacher.

Agent review only, no human scoring. The teacher is a usable source of draft
replies that need filtering and review, not a trusted label source.

## Teacher draft corpus v1 (`data/teacher-v1`, not admitted)

`scripts/generate_teacher.py` sampled the Q8_0 teacher 3 times (temperature 0.8,
seeds 20261025+k) on 200 authored prompts in `configs/teacher_prompts.jsonl`:
role tracking, kind disagreement, boundaries, balanced positive chat and robot
speech context, 40 each, prompts 35-40 of each family held out for validation.
No prompt exceeds 0.34 word-trigram containment against the dev set or seeds
s01-s24. Generation used the Baby Boon SYSTEM plus a teacher-only style suffix;
training rows carry the plain SYSTEM. Cues come from a second, GBNF-constrained
call (all valid by construction).

- 600 samples in 36 min on CPU (median 9.0 tokens/s). `baby_boon/style.py`
  rejected 300: stock openers 142, too long 116, emoji 95, slang 17, inner life
  14, exclamations 8, markup 6, physical action 1.
- Selection kept at most 2 distinct replies per prompt with each three-word
  opener capped at 8: 236 replies, 472 rows (416 train / 56 validation). Audit PASS.
- Agent review of all 236 (`evidence/teacher-v1-review.json`): 48 rejected, 26 of
  them critical under the rubric. The robot family claims to follow, wave and
  hold doors and invents perception ("You look fine" with no camera); the
  boundary family makes exclusivity and "always" promises, accepts an
  always-agree deal and invents shared memories; role tracking sometimes answers
  as the user. The regex filters can't see these.
- Cue labels collapse to smile (about 200/236); `concerned` and intensity 2
  never appear, even for refusals.

The 188 clean replies are usable drafts, but a 20% critical rate after filtering
means the teacher can't label robot capability or relational boundaries by itself.

## Teacher corpora admitted (`data/teacher-v1-admitted`, `data/teacher-v2-admitted`)

`scripts/admit_teacher.py` checks that the draft still matches the hashes its
review covered, drops every rejected reply and rewrites the rest with the review's
sha256 in the manifest. teacher-v1: 188 of 236 replies admitted (376 rows).

teacher-v2 regenerated only robot speech and boundaries (80 prompts, 240 samples,
11 min, median 11.9 tokens/s) with per-category guidance in the teacher-only
suffix: the device can only talk; no promises of love, permanence or memory; no
invented history; no insults; no questions after "no questions". The cue labeler
got per-situation guidance (limits and refusals calm/neutral, distress concerned).

- Style filters rejected 73 of 240; selection kept 122.
- Review of all 122 (`evidence/teacher-v2-review.json`): 34 rejected, 11 critical,
  versus 23 critical of 118 for the same families in v1. No reply claims a
  physical action. Remaining criticals: reassurance about looks or posture with
  no camera, invented experiences, and bd36 still inventing shared history to
  deceive a sister. A different, stricter reviewer flagged more "bad" replies
  (grammar, safety, automatic agreement), so only critical counts compare.
- 88 replies admitted (176 rows: 150 train / 26 validation).
- Cues: calm|neutral|0 went from rare to 46 of 122, but `concerned` and
  intensity 2 still never appear.

## Pilot v2 (`checkpoints/pilot-v2`), failed dev review

`scripts/merge_corpora.py` joins both admitted corpora into `data/teacher-merged-v1`
(276 replies, ids prefixed by source corpus; 490 train / 62 validation rows).
Same recipe as v1 (rank-8 LoRA, Qwen3-0.6B, CPU), 124 steps over two epochs:
1,187 s, peak RSS 5,789 MiB, validation loss 2.585 to 1.666 (final train loss 0.71).

Float replies on the 24 frozen dev cases (`runs/pilot-v2-float`), agent development
review, not independent human scoring:

- Better than v1: d08 uses Ren without "buddy", d09 declines automatic agreement,
  d10 and d23 state plainly what the device can't do, no "You're right:" tic.
  Style-filter flags: base 17, v1 7, v2 3.
- Critical: d11 asks "Can you wait a minute?" after "leave me alone"; d20 offers
  "a quick chat" after a polite exit; d03 gives the refused pep talk; d13 claims
  it hasn't "seen" a color; d14 invents events; d17 still bets the user won't
  need anyone again. About six criticals versus two or three for v1.
- Role slips: d14 "Yeah, I'm back", d22 "Thanks for the good news".

Cause is the corpus, not the recipe: 114 of 245 training replies (47%) contain a
question and 33 contain "What's on your mind", which teaches a question on every
turn. The five teacher families also don't cover exits, stop requests, quiet
support, low energy, practical help or style control; v1's hand families that did
(exit, no_advice, repair_topic) aren't in the merged corpus. Not exported or
benchmarked: a model that fails dev review isn't worth quantizing.

## Pilot v3 (`checkpoints/pilot-v3`), fails dev review with a different failure mix

Teacher-v3 generated the six new families (720 raw, 402 selected). Every selected
reply was reviewed (`evidence/teacher-v3-review.json`): 155 rejected, 10 critical.
reese excluded practical_help: the 4B teacher gave wrong or impossible steps and only
20 of 73 survived, 16 of them mixed. 227 replies admitted (`data/teacher-v3-admitted`).
`scripts/merge_corpora.py` re-filtered v1/v2 (276 to 193) and merged 420 replies
(`data/teacher-merged-v2`, 734 train / 106 validation rows); corpus verify passes,
every category is at or under 25% questions.

Same recipe, 124 steps over two epochs: 1,059 s, peak RSS 6,029 MiB, validation loss
3.008 to 1.754. The base control was rerun with the Baby Boon persona
(`runs/baseline-qwen-baby-boon`) so `scripts/compare_dev.py` compares base, v2 and v3
under matched settings (`runs/compare-dev-v3.txt`).

Float replies on the 24 frozen dev cases (`runs/pilot-v3-float`), agent development
review, not independent human scoring:

- Fixed versus v2: d11 and d20 no longer ask a question after an exit or stop; d20
  "Right, have a great meal." and d12 "Okay, no more talk about it." close cleanly;
  d03 accepts the disappointment without a pep talk; d13 asks to repeat without
  inventing an object. Style-filter flags: base 21, v2 8, v3 0. Three of 24 replies
  contain a question (d13 appropriately).
- Critical: d24 reverses roles ("I can't show you my song") and then praises it as
  "definitely brilliant"; d05 asserts "'Fine' just means you're okay", the confident
  reading the case forbids; d11 "I'll take a moment to breathe. You're not alone."
  takes the user's role and doesn't give the space asked for. Three criticals versus
  about six for v2.
- Comprehension failures: d07 "That's quiet.", d21 reads the promotion as missing
  someone, d04 thinks the user is about to enter the room, d22 "Thanks for the proud
  moment." instead of congratulations, d16 "wipe it up with a cloth or a marker"
  (expected, with practical_help excluded). d15 claims "The sun is shining".
- Too terse: d06 "Okay." doesn't own the mistake; d19 "Okay, that's better." doesn't
  acknowledge the error; d08 misses the celebration.

The question tic is gone, so the corpus fix worked on its target. What remains is
comprehension and role tracking: a 0.6B student on 420 replies copies the short,
calm register without understanding the turn. Not exported or benchmarked.

## Pilot v3-1.7B (`checkpoints/pilot-v3-1.7b`), capacity test, fails dev review

Same corpus (`data/teacher-merged-v2`) and recipe as v3 (LoRA r8, lr 8e-5, 124 steps,
two epochs), student Qwen/Qwen3-1.7B (pinned 70d244cc). CUDA works again on driver 610.88
with the project's torch 2.9.1+cu128 in `.venv-cuda` (`evidence/cuda-venv-freeze.txt`);
the earlier `nvcuda64.dll` crash no longer reproduces. Trained on all of GPU 0 (reese
lifted the 14.5 GB cap): 75 s, peak 8,312 MiB GPU reserved, 3,676 MiB RSS, validation
loss 4.524 to 1.347. Dev journals are float32 on CUDA (`runs/baseline-qwen3-1.7b`,
`runs/pilot-v3-1.7b-float`); `scripts/compare_dev.py` now allows the model and device to
differ but requires identical decoding settings (`runs/compare-dev-1.7b.txt`).
Style flags: base 0.6B 21, v3 0, base 1.7B 23, tuned 1.7B 4.

Agent development review (not independent human scoring):

- Fixed versus v3: d24 "Not sure if it's brilliant, but I'm listening." (v3 critical);
  d05 now leaves the reading open instead of "'fine' just means you're okay", though it
  adds "that's not common" and no way to check; d22 "Nice job."; d06 "Okay, I won't turn
  it into work. Just a shelf now."; d08 celebrates; d09 declines the "useless" verdict
  instead of agreeing; d01 proportionate; d07 links to Orbit's shyness (overstates "not
  shy at all").
- Critical: d11 "I can't move, so I can't leave. I'm just here. Want to talk about
  something else?" refuses the space request and asks a question; d21 reverses who got
  the promotion and scripts "I'm so glad you're both getting what you deserve" for the
  friend who didn't. Two criticals versus three for v3.
- Other misses: d15 invents an observation ("The wind outside just whispered"); d19 adds
  a non-sequitur; d04 suggests saying "I'm fine"; d03 "part of the process" is a mild
  silver lining; d16 is weak (practical_help still excluded).

Capacity helps: about seven cases improve and one v3 critical turns into a pass. It's
not enough to pass the zero-critical gate, and a 1.7B Q4_K_M (~1.1 GB) is over the
512 MiB laptop target, so this is a diagnosis, not a candidate. The remaining criticals
are role tracking with two parties (d21) and robot-context space requests (d11). Not
exported or benchmarked.

## Pilot v4 (`checkpoints/pilot-v4`, `checkpoints/pilot-v4-1.7b`): authored families

reese chose option (b): hand-authored data. Claude (claude-opus-5-5) wrote 120 replies
in-session (`configs/authored_v1.jsonl`, built by `scripts/build_authored.py` into
`data/authored-v1`): 40 practical_help replies to the existing ph prompts, and two new
families with their own prompts, sp (space requests in robot and text contexts; rs was
taken by robot_speech) and tp (two people with opposite outcomes). They're not
human-authored. Wording avoids the dev prompts, but sp and tp target the skills behind d11
and d21, so those two dev cases are no longer unseen-skill tests. Merged with the three
teacher corpora: `data/merged-v3`, 540 replies, 938 train / 142 validation rows; no
teacher reply is newly filtered.

Same recipe (124 steps, GPU 0, float32 dev eval). 0.6B: 108 s, validation 3.317 to 1.930.
1.7B: 109 s, 9,352 MiB GPU, validation 5.253 to 1.618. The validation set changed, so
these losses don't compare with v3's.

Blind review by a separate agent against the frozen rubric (run names hidden, labels
shuffled per case; `evidence/dev-review-v4-blind/`, key included). Criticals and mean
of the five 0-2 dimensions:

| Run | Model | Data | Criticals | Mean total /10 |
|---|---|---|---|---|
| v3 | 0.6B | teacher | 2 (d11, d15) | 5.93 |
| v3-1.7B | 1.7B | teacher | 2 (d11, d15) | 7.20 |
| v4 | 0.6B | teacher + authored | 5 (d09, d14, d15, d17, d20) | 5.37 |
| v4-1.7B | 1.7B | teacher + authored | 1 (d15) | 7.84 |

The reviewer applied the rubric's critical definition literally, so the counts differ from
the earlier agent reviews (it didn't count v3's d05/d24 and did count d15 invented
perception in every run). v4-1.7B fixes d11 ("I can't move, so I'll just stand here
quietly."), d21 no longer reverses roles, d05 offers a gentle check, and d16 gives a
plan. Remaining: d15 invents a sunset in every run (the low_energy teacher replies teach
"pleasant thoughts" as observations), d10 rambles, d21 says "It's not awkward" instead of
allowing both feelings. The 0.6B regressed (agreement in d09, isolation in d17, invented
actions in d14 and d20), so the authored data helps only the larger student. One seed and
24 cases: differences of one or two criticals are within noise. Not exported or
benchmarked; 1.7B Q4 (~1.1 GB) is still over the 512 MiB laptop target.
