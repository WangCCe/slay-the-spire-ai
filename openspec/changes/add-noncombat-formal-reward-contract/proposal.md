## Why

The completed formal-RL readiness audit passed state/action and evaluation but
blocked on the absence of a separately tested formal reward contract. The
existing floor-progress plus victory return is authorized only for a simulator
training smoke and does not define the primary/secondary objective relationship
required by a later formal training proposal.

## What Changes

- Add one versioned, hash-bound formal non-combat reward contract with terminal
  victory as the primary objective and floor progress as a separate secondary
  simulator shaping channel.
- Require either lexicographic optimization or a scalarization proof that a
  victory strictly dominates the complete bounded shaping range; do not promote
  the smoke's `victory_bonus=1.0` into a formal default.
- Bind fixed formula examples, terminal semantics, Current/Bottled/SimpleAgent
  exclusions, simulator/live provenance separation, implementation identity,
  and all-false execution authority.
- Publish one deterministic contract artifact and focused validation report,
  then create a new read-only formal-RL readiness registration that consumes it.
- Require the new readiness result to change only the reward domain from
  blocked to passed while preserving the baseline-policy and outcome-support
  blockers and the overall no-go verdict.
- Run no gameplay, simulator rollout, native module, model fitting, RL,
  qualification, OPE reinterpretation, live loading, or promotion.

There is no new live evidence. Success is exact reproduction of the contract
artifact and an updated readiness matrix with `reward=passed`,
`baseline_policy=blocked`, `outcome_support=blocked`, and every execution or
promotion authority false. Rollback removes only this change, the contract
validator/tests/artifacts, and the new readiness registration/report; the
previous readiness audit remains immutable.

## Capabilities

### New Capabilities

- `noncombat-formal-reward-contract`: Defines terminal-victory priority,
  bounded secondary floor shaping, reference exclusions, provenance, fixed
  verification, and no-authority publication for later formal RL design.

### Modified Capabilities

- `noncombat-formal-rl-readiness-audit`: Adds the positive reward-domain
  scenario and the immutable re-registration boundary for a validated formal
  reward contract.

## Impact

- Adds one small offline contract module, focused tests, a frozen contract
  registration/report, and one new readiness-audit registration/report.
- Reads existing reward implementation, tests, specs, and frozen readiness
  evidence without changing production agent behavior, simulator reward code,
  live configuration, models, checkpoints, policies, or external repositories.
- Adds no runtime or third-party dependency. A passing reward domain remains
  insufficient for a bounded-training proposal while the registered baseline
  and outcome blockers remain.
