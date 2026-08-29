# Action-relative live context target audit

## Decision

Existing no-takeover live-shadow evidence supports replacing the broad
all-transition replay target with real guard-replacement opportunities for an
independent confirmation design. It does not yet authorize fitting or training.

## Evidence

Four sealed parent-policy live sessions spanning 20 runs contain 768
guard-replacement opportunities. Every shadow row joins uniquely to an
in-combat decision-state row with the same floor and turn; the maximum
timestamp difference is 14 ms. All sessions bind the same production-parent
parameter hash and grant the candidate no action-takeover authority.

Against these opportunity states, the merged 5,000-row fresh successor corpus
passes every existing support threshold:

- real-context coverage `0.940104`;
- ESS `872.930` and maximum normalized weight `0.009695`;
- floor-23-27 coverage `1.0` and floor-28-34 coverage `0.757143`;
- weighted floor, HP, potion, and relic SMD `0.205608`, `0.186789`,
  `0.023366`, and `0.030744`.

The same corpus fails when every r14/r15 replay transition is treated as the
target. That population includes ordinary card actions and non-replaced end
turns which the successor collector intentionally excludes. The resulting
coverage failure therefore does not measure deployment-opportunity support.

## Boundary

Rows are clustered within 20 runs across four continuous sessions, and these
runs informed the target definition. A new run- and session-disjoint
parent-only live holdout is required before changing the support contract. The
holdout must retain exact guard-replacement telemetry and context state, and
must not give any experimental candidate action authority.
