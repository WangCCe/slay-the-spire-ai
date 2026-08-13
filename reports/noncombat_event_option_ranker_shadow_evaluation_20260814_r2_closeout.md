# Event Option Ranker Fresh Shadow Closeout

## Verdict

`event_ranker_shadow_benefit_replicated`

The exact committed event model replicated its Current-relative simulator
benefit on the fixed disjoint `94400..94463` cohort. This permits a separate
paired full-trajectory simulator-shadow proposal. It does not authorize live
gameplay, production loading, qualification, promotion, or additional tuning.

## Evidence

- 119 complete sources, 56 informative sources, and 19 event ids
- Current mean/p95/max regret: `0.064721 / 0.298246 / 0.508772`
- Selected mean/p95/max regret: `0.046292 / 0.298246 / 0.298246`
- 86 action changes: 23 corrected and 16 worsened
- Unique-best accuracy improved from `0.403846` to `0.557692`
- All nine fixed support, diversity, regret, and change gates passed
- One Courier censor and one exact Current shop mapping censor

Corrections covered 11 event ids. World of Goop, Shining Light, Transmorgrifier,
Golden Shrine, and Accursed Blacksmith contributed meaningful gains. Golden
Wing, Living Wall, and Upgrade Shrine had net regret increases and remain
important full-trajectory risks.

## Confidence Limitation

All 86 learned disagreements had confidence between `0.500285` and `0.507894`.
The bound `0.50` threshold again accepted every disagreement, so replication is
evidence for the raw ranker, not for calibrated conservative fallback behavior.

## Preterminal R1

The original `94300..94363` attempt stopped before a policy verdict at an
unregistered `shop + candidate_mapping_absent` continuation boundary. Those
seeds were not reused. The exact boundary is now a registered source censor;
all other mapping failures remain fatal. R2 retained the exact model, threshold,
resource limits, and verdict gates.

## Integrity

- Four manifest-bound artifacts matched byte size and SHA-256 identity.
- The fresh dataset round-tripped byte-for-byte and bound seeds `94400..94463`.
- Shadow access count was one; model fitting and training were false.
- Focused bridge/ranker/shadow tests passed: `20 passed in 11.29s`.
- Strict OpenSpec validation passed.

## Next Step

Run a paired full-trajectory simulator shadow on disjoint seeds: Current on one
arm and Current-with-bound-event-ranker on the other. Compare terminal victory,
floor progress, aggregate return, event override frequency, and unsupported
trajectory rate. Do not integrate the model into gameplay unless that paired
effect also passes fixed noninferiority and support gates.
