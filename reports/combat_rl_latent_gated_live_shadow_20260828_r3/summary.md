# Combat RL Latent-Gated Live Shadow r3

## Decision

The source-bound candidate is eligible for a separately bounded matched gameplay evaluation. This result does not authorize candidate action takeover, training, promotion, or a gameplay-quality claim.

## Shadow Evidence

- Production r16 controlled all five fresh games; the candidate remained shadow-only.
- The trace contains 300 policy decisions plus two audited transient `WaitAction` discards, with no runtime errors.
- Parent parity, candidate legality, and final executed-action legality were all 100%.
- Candidate-parent disagreement was 45.67%; the candidate matched the final guard-processed action on 58.00% of policy decisions.
- Adapter inference p50/p95/maximum latency was 11.37/20.31/113.41 ms. The registered p95 ceiling was 100 ms.

## Live Reconciliation

- All 302 proposals paired with one `RL returned` line and one final callback; no unmatched or trailing proposal remained.
- Proposal-to-`RL returned` p50/p95/maximum was 18/28/293 ms.
- Proposal-to-final-callback p50/p95/maximum was 42.5/922.15/2799 ms. The post-model guard and commit phase accounts for the high tail, with p95 907.6 ms; this is not attributed to the shadow adapter.
- The CommunicationMod log grew by 1,879 bytes and contained no traceback or exception signature.
- Five AI markers and five `.run` files were produced. Floors reached were 19, 16, 16, 33, and 16; all runs ended in defeat.
- The pre-experiment CommunicationMod configuration was restored byte-for-byte and the started game/Python processes were stopped.

## Provenance Note

r2 produced an apparent 99.49% executed-action legality result because two stale-state refresh `WaitAction` commands were treated as policy actions. The r3 source explicitly audits these commands as transient discards. The fresh r3 cohort covered this branch twice and passed every preregistered readiness criterion.
