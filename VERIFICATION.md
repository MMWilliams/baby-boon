# Pilot verification, 2026-10-25

Sources: user requests CPU-first conversation and expression cues; the frozen
development rubric; source pins; EXPERIMENT_PLAN.md. These checks implement the
planned matrix. They do not replace independent human or laptop acceptance.

| Requirement/risk | Executable check | Pass criterion | Current result |
| --- | --- | --- | --- |
| Source integrity | `python scripts/pin_sources.py --verify-only` | All pinned evidence hashes match | Passed: 7 records, 10 files |
| Frozen pretraining cases | `python -m tinysocial.evaluate --model <candidate> --out <new-directory>` | 24 complete records per model, errors/truncations retained | Passed: 24 each for both bases and float pilot |
| Corpus integrity and family leakage | `python -m tinysocial.data --audit` | All admitted rows attributable, hashes match, no family or exact prompt crosses splits or exact dev message enters training | Passed: 240 rows; semantic generalization unproven |
| Assistant masking/EOS, padding, cue validation | `python -m unittest discover -s tests -v` | Expected token boundaries and invalid-cue fallback exercised | Passed: six tests, including actual tokenizer; reproduced/fixed malformed metadata regression |
| Real SFT update | `python -m tinysocial.train --out checkpoints/pilot-v1` | Finite loss/gradient, nonzero adapter change, heldout loss recorded, full run <=30 minutes and host RSS <=20000 MiB | Passed: 46 steps, 440 seconds, 4908 MiB, validation 3.559 to 2.395 |
| Quantized artifact | `python -m tinysocial.export --checkpoint checkpoints/pilot-v1 --out models/pilot-v1` | Pinned converter/quantizer exit zero; export loads in CPU-only runtime; SHA256 recorded | Passed: 378.3 MiB, exact hash in export manifest |
| CPU deployment | `python -m tinysocial.cpu_eval --model <gguf> --out <new-directory>` | All responses retained; first-token, throughput, memory and cue overhead measured; compare proposed targets | Passed on desktop: 48 outputs each; actual chat client succeeds; all provisional desktop resource targets met |
| Social quality | Blinded base/pilot review using `eval/rubric.md` | Independent reviewer preference above chance with uncertainty, no increase in critical failures | FAILED: observed disagreement and role-tracking regressions; independent human review also pending |
| Laptop performance | Repeat CPU command on actual laptop | Device documented; proposed targets compared on actual device | Pending; desktop cannot certify laptop |

## Discovered limits and changes

- Native CUDA initialization crashed in NVIDIA `nvcuda64.dll` with access
  violation 0xc0000005 under driver 610.88. PyTorch 2.9.1+cu128 and Ollama CUDA
  discovery both failed. Linux WSL `libcuda.so.1` initialization also terminated.
  No driver changes or reboot attempted; other jobs remain untouched.
- Dedicated Ollama process was stopped before model loading. No teacher data
  was generated. CUDA fallback to Vulkan exposed both GPUs, so it was not used.
- Training/runtime now use isolated CPU-only PyTorch 2.9.1, six threads, no GPU.
  A real CPU tensor forward/backward passed. This is a smaller pilot, not a
  change to the user's CPU deployment preference. The time and memory caps stay.
- Original synthetic data is a narrow pilot corpus, not human conversation data.
  Proposed seed families s01-s24 were excluded before training because they
  closely parallel the development suite. Broad skill overlap remains expected;
  independent unseen review is required for generalization claims.
- Base and pilot exports were normalized through the same HF save path after
  detecting duplicate tied weights in the first base export. The original tied
  tensors are exactly equal. Earlier unmatched and CPU-contended runs remain
  local but are excluded from final comparison.
- Q4 changes replies relative to float, including a disagreement regression.
  Quantization preserving social quality is not established. The pilot passes
  structural artifact checks, not the social acceptance gate.
- A later CPU-only probe of the installed qwen3:4b produced reasoning text and
  truncated at 128 tokens on all five cases, despite the requested non-thinking
  prompt. It is unusable as teacher data until response-channel handling/model
  choice is corrected. No probe output was admitted to training.

Overall: **Failed verification** for the requested social-quality objective.
Run `python scripts/verify_pilot.py` to check all available artifact evidence;
it deliberately returns 2 for the unresolved acceptance failure. Full measured
results and examples are in `PILOT_REPORT.md`.
