# Collision-Free Encounter Identity Result

## Decision

Retain `r4`. Do not run a frozen confirmation and do not transfer either
candidate to live gameplay.

Both registered policy comparisons passed. The enum-v1 candidate improved over
`r4` by `+1.449` mean reward and `+1.137` mean player HP across 842 reachable
profiles, with candidate-only victories `19:6`. At battle index 9 the deltas
were `+4.031` reward and `+2.881` HP, with victories `6:1`.

The collision-free encoding also beat the matched hash arm on every registered
head-to-head criterion. Across all 1,024 registered profiles its reward delta
was `+0.151` and victories were `5:1`; at battle index 9 its reward delta was
`+0.466`, HP delta was `+0.094`, and victories were `2:0`.

## Technical Gate

Both arms reported `technical_smoke_ready`, used identical source replay
metrics and parent control rows, completed 256 optimizer updates, preserved
parent behavior through zero-column migration, and produced no evaluation
truncations. Enum-v1 assignments were unique and the vocabulary hash matched
the registration.

However, each arm contained two training profiles that reached the registered
100-decision bound. The registration required zero training decision-bound
truncations. Because that criterion failed, the otherwise positive policy
result cannot authorize the fresh frozen confirmation. The bound will not be
changed after outcome access.

This remains simulator-only evidence and grants no gameplay, transfer,
qualification, promotion, mechanics-equivalence, or live policy-quality
authority.
