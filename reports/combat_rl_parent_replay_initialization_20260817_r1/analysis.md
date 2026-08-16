# Parent weights with historical replay initialization

## Purpose

Initialize bounded parent-EndTurn imitation training without inheriting a
rejected successor's network or optimizer state and without spending roughly
20 live games rebuilding the replay threshold.

## Construction

The online network, target network, and frozen anchor are exact copies of the
promoted parent. The 4,096-transition replay snapshot and its source transition
counter come from guard-intervention r2. Optimizer state is empty, episode is
reset to zero, and the targeted imitation weight is `0.20`.

## Verification

The artifact round-tripped with exact parent tensors and an empty optimizer.
`RLAgentV2` loaded it in CPU training mode with the production item mapping;
one in-memory train step produced finite loss and selected 55 targeted replay
states. This initializer has training authority only and no promotion
authority.
