# Outcome-Backed Route Ranker Closeout

## Decision

The fixed route counterfactual experiment is terminal as
`route_counterfactual_ranker_not_ready_after_development`. Do not tune the
epoch schedule, model, features, or gates against development seeds
`93128..93159`, and do not load the trained model into gameplay.

The model learned useful ordering signal: development weighted pairwise
accuracy rose from `0.512676` to `0.631925`, and unique-best accuracy rose from
`0.456522` to `0.565217`. It did not beat Current policy: mean regret changed
from `0.042495` to `0.042690`, maximum regret increased from `0.298246` to
`0.508772`, and 42 action changes contained 10 corrections and 10 regressions.

## Evidence

- Exact executed source and artifacts are committed at
  `10f072d3cc65c00f1cdc1c64caac183bec597c78`.
- The terminal bundle contains 369 train route sources, including 224 with
  unequal returns, and 90 development sources, including 54 with unequal
  returns.
- All six canonical manifest entries, both dataset round trips, the model state
  round trip, and the source-file hashes were independently verified.
- The adjacent focused suite passed 158 tests; the full repository suite was
  intentionally not run.

## Provenance Correction

The canonical report bound the runner, branch credit, projection, and ranker
files but omitted the Current-policy bridge source from its source-file list.
The exact bridge used by the run is preserved in the executed-source commit:

- Path: `analysis_scripts/noncombat_current_policy_simulator_bridge.py`
- SHA-256: `1bbcd6008c78338b76b9d95e28d52e95a997734542b5a27fc9896bacb7c8ffce`
- Size: `102865` bytes

The canonical `report.md` also incorrectly describes downstream continuation
as native SimpleAgent. The executable used a fresh frozen
`CurrentPolicyBridgeSession` for each forced branch and re-decided every
post-action transition with Current policy; only the root source-sampling
trajectory used native continuation. The original terminal bundle remains
unchanged. Future runner reports bind the bridge source and use the corrected
wording.

## Next Direction

Stop this route model configuration. The next empirical work should move to an
event-option counterfactual outcome POC, where reachable semantics are closed
and the missing evidence is action-level credit, rather than continue route
architecture tuning on the consumed development cohort.
