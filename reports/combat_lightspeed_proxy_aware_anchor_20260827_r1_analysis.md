# Proxy-aware parent anchor ablation

## Verdict

`negative_reject_proxy_aware_anchor_retain_raw_parent`

Both arms were technically valid, but the proxy-aware label objective regressed the matched fresh cohort. Keep `frozen-parent-greedy-v1`, do not combine the proxy-aware objective with encounter identity, and do not tune or repeat this cohort.

## Technical result

- Both arms: `technical_smoke_ready`, 49,984 source transitions, 66,152 prepared transitions, and 256 optimizer updates.
- Source transition identity, replay preparation, replay targets, and frozen-parent evaluation rows matched exactly.
- Both arms observed 20,888 collected guard replacements.
- Control used zero executed-action anchor overrides.
- Candidate used 13,656 sampled overrides across updates, mean 53.34375 per update.
- Both manifests verified; both reports had no blockers, unexpected initialization failures, or unsupported successors.

## Policy result

Candidate minus raw-parent control over 832 matched terminal profiles:

| Battle | Profiles | Reward delta | HP delta | Candidate-only wins | Control-only wins |
|---:|---:|---:|---:|---:|---:|
| 0 | 256 | -0.7644 | -1.1992 | 0 | 0 |
| 3 | 246 | -0.3855 | -0.8699 | 3 | 2 |
| 6 | 195 | -2.1586 | -0.5179 | 4 | 13 |
| 9 | 135 | +1.0465 | +0.8593 | 5 | 5 |
| **All** | **832** | **-0.6853** | **-0.6082** | **12** | **20** |

The combined battle-6/9 reward delta was `-0.8474`. Every pre-registered candidate-minus-control criterion failed. Candidate minus r16 was also negative: reward `-1.2707`, HP `-1.1250`, and victories `11:27`.

## Interpretation

The replacement provenance and mixed-label implementation worked as intended, so this is a policy result rather than a technical ambiguity. Directly imitating every guard-replaced executed card over-corrects the parent anchor under this replay recipe, especially at battle index 6. The opt-in mechanism remains useful for controlled research, but the default and authoritative label mode remains the raw frozen-parent greedy action.

No gameplay, CommunicationMod, packaging, qualification, or promotion is authorized by this experiment.
