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
