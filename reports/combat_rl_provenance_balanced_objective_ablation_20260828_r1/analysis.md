# Provenance-Balanced Objective Ablation

## Decision

No objective recipe is recommended. Both fixed 64-update arms failed only the
preregistered direct parent disagreement ceiling of 10%, so neither output has
candidate, holdout, gameplay, qualification, promotion, policy-quality, or
production authority.

## Results

| Arm | Direct drift | Overall drift | Override-label uplift | Validation TD | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Global anchor reference | 35.85% | 62.88% | 28.98 pp | 3.4115 -> 3.0776 | direct drift failed |
| Balanced anchor | 26.42% | 58.52% | 29.26 pp | 3.4115 -> 3.1861 | direct drift failed |
| Balanced anchor + direct margin | 22.64% | 58.08% | 25.85 pp | 3.4115 -> 3.3980 | direct drift failed |

Balancing direct and override anchor strata reduced direct drift by 9.43
percentage points relative to the fixed global-anchor reference. Adding the
direct-only margin guard reduced it by another 3.77 points, for a total
improvement of 13.21 points. The guarded arm still changed 24 of 106 direct
validation actions, more than twice the allowed rate.

Both arms retained material overall movement, positive override-label uplift,
improved validation one-step TD, bounded positive-energy End Turn behavior,
finite objectives, exact 64-update budgets, both provenance strata in every
training batch, and exact checkpoint round trips. The guarded arm traded 3.41
percentage points of override uplift for its additional 3.77-point direct
stability gain.

## Independent Audit

- The registration, replay checkpoint, fixed reference report, and direct-margin
  audit hashes match the report bindings.
- The replay checkpoint SHA-256 is
  `606727df27dd82ac825767097b71f07d6aa39ad37e0ea5d5d432e88c9288c28f`.
- Frozen online and target state dictionaries both hash to
  `23491db97fe31cf12052207ea321b4c2ac23a922f2a0916a3dc54d604ee3a720`;
  the optimizer state is empty.
- The balanced checkpoint file hashes to
  `449d44b358328fbaf2daf4a293749a860128b4a01295194be031937513a28e03`,
  and its online state dictionary hashes to
  `0866a9d9e542a86f0142819a533a6da5f1a12a6c750f558463db1d8d0d91fb00`.
- The guarded checkpoint file hashes to
  `aa3707134b84ae8c3537fc39f7f1d5bc27dd088b0c70c746f676b50bfb296fd8`,
  and its online state dictionary hashes to
  `5613a540bba2e1a3c99585aac9f1ab4b86edbad7a9fc07619e286789ea8a49d7`.
- The report grants training/model-fitting authority only for this completed
  objective-design run; every downstream authority field is false.

## Interpretation

The monotonic direct-stability improvement supports the cross-stratum
interference hypothesis, but scalar reweighting and a direct-only ranking loss
are insufficient. The remaining high direct drift is not a reasonable target
for an unregistered weight, cap, seed, or update-count sweep on this reused
corpus.

The next investigation should isolate learned override behavior from the base
combat Q function through a residual or separate head. That architecture must
default to the frozen parent behavior when no eligible override signal is
present, expose the residual contribution in telemetry, and remain an offline
development ablation until a fixed design passes direct-stability and override
uplift gates. Only then should a new replay be collected for a final candidate.
