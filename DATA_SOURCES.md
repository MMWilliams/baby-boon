# Data source review

No external conversation dataset has been admitted to training. Publisher metadata is
an intake signal, not a completed provenance/quality review. Preserve source
IDs and licenses on every accepted conversation. Do not read or train on local
personal chat databases, private conversations, or customer records.

| Source | Publisher-declared license / status | Proposed role |
| --- | --- | --- |
| [OpenAssistant/oasst1](https://huggingface.co/datasets/OpenAssistant/oasst1) | Apache-2.0 in publisher card; original tree schema and per-row review pending | Human-authored multi-turn grounding; select relevant English trees and review quality |
| [HuggingFaceTB/smoltalk](https://huggingface.co/datasets/HuggingFaceTB/smoltalk) | Mixture; constituent terms and generation provenance require separate review | Candidate conversational/rewrite subsets; do not blanket-admit the mixture |
| [HuggingFaceH4/ultrachat_200k](https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k) | MIT in publisher card; synthetic-data provenance/terms review pending | Possible small general-dialogue retention component |
| [facebook/empathetic_dialogues](https://huggingface.co/datasets/facebook/empathetic_dialogues) | CC BY-NC 4.0 in publisher card | Excluded from the intended redistributable training pool; no dataset downloaded |
| Newly authored scenarios and licensed local-teacher outputs | Record author/generator, model revision, prompt family, generation settings, rights and reviewers | Target social skills and expression cues; synthetic examples must be labeled as such |

Data should span ordinary small talk, shared activities, humor, celebration,
frustration, disappointment, social ambiguity, mild disagreement, boundaries,
repair, and everyday robot interactions. Emotional-support dialogue alone is
not representative of the requested capability.

Keep all branches of one source conversation in the same split. Cluster exact
and near duplicates and synthetic prompt families before splitting. The final
evaluation must be independently authored/reviewed and excluded from prompts
used to generate training data. Do not manufacture a favorable final score by
relabeling development examples as a holdout.

Initial corpus sizes and mixture proportions remain experimental choices.
Start with a small, inspectable pilot rather than generating a large unchecked
synthetic corpus. Score naturalness, appropriateness and continuity; avoid
rewarding stereotyped emotion labels or automatic agreement.

## Pilot v1 admission

The local pilot uses `original-fictional-v1`: 120 synthetic conversation targets,
each represented in plain and cue modes (240 rows). There are 184 training rows
and 56 validation rows. All are Codex-assisted original examples assembled from
`configs/seeds.jsonl` and `baby_boon/data.py`. They are not human conversation
records. No external dataset, private chat, personal database or teacher service
was used. Broad linguistic/social coverage is deliberately limited at this stage.

Seed families s01-s24 were rejected before training because their structure
closely parallels the development cases. The remaining source seeds and all
template outputs were reviewed during construction for the intended response,
capability honesty and valid presentation labels. Sibling plain/cue examples
and each entire generator family stay in the same split. The audit checks hashes,
source labels, exact prompt overlap, family membership and cue validity; it is
not a semantic deduplication model or a human-quality certification.

The validation split has four whole seed families and two whole template
families. The authored dev suite is separate but covers related skills. Neither
this small validation set nor the development suite establishes broad social
generalization. Independent unseen human evaluation remains required.

Reproduce with `python -m baby_boon.data`; verify the immutable output with
`python -m baby_boon.data --audit`. The exact corpus manifest is saved alongside
the experiment evidence after training; the full generated rows remain local.
