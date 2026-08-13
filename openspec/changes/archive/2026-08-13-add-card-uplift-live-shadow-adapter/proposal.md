## Why

The frozen card-uplift candidate improved paired simulator terminal floor by
`6.671875` with a positive 95 percent interval and two victories versus zero.
Before it can affect gameplay, the project needs direct evidence that live
CommunicationMod card rewards can be projected, scored, and recorded without
changing the Current action.

## What Changes

- Add an opt-in, configuration-bound card-uplift shadow runtime around the final
  live state callback.
- Project ordinary non-combat three-card rewards into a documented
  `live-best-effort-v1` feature boundary and load the exact frozen r7 entry and
  residual bytes.
- Append current-versus-shadow choices, scores, projection diagnostics, model
  identities, and errors to a dedicated JSONL file while returning the exact
  Current action object.
- Run at most five fresh no-training games and require at least 12 complete
  eligible rows, no action substitution, no runtime error, and at least three
  disagreements before considering a separate intervention canary.

## Capabilities

### New Capabilities

- `noncombat-card-uplift-live-shadow`: Defines opt-in live projection, frozen
  scoring, fail-open observation, evidence, cohort gates, and no-intervention
  authority.

### Modified Capabilities

None.

## Impact

- Adds one small runtime module, focused tests, one startup hook, and one batch
  wrapper option.
- Loads the tracked CPU model only when an explicit bound config is present.
- Does not train, change an action, enable exploration, or promote the policy.
  Rollback is removing the shadow config/argument; Current gameplay remains the
  decision owner even if scoring or persistence fails.
