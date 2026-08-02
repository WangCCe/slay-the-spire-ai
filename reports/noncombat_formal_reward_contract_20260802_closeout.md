# Non-Combat Formal Reward Contract Closeout

Date: 2026-08-02

## Result

The source-bound formal reward contract is complete and strictly reproducible.
It defines terminal victory as the primary objective and floor progress as a
separate simulator-only potential-shaping channel. A future optimizer must use
victory-first lexicographic ordering or prove a scalar victory weight strictly
greater than the maximum complete-episode shaping contribution of `1.0`.

The existing smoke reward's `victory_bonus=1.0` is therefore not automatically
formal-compatible, and this change selects no replacement weight, algorithm,
model, or policy.

## Frozen Identity

- Implementation commit: `e3fde0cc9fc88809a55463429256d8576fb766dc`
- Contract registration: `reports/noncombat_formal_reward_contract_20260802_input.json`
- Registration SHA-256: `dcda155c98f3bf76dd60df5236a62792ad85510dd94b82f97883d05e5afaad81`
- Canonical artifact directory: `reports/noncombat_formal_reward_contract_20260802`
- Contract SHA-256: `4ee9c0087e523b95e2d380d6e6a0c7ecefd4f211cbd7d780b496df0d642a10bb`
- Contract verdict: `formal_reward_contract_ready`

Strict recomputation reproduced every canonical configuration, contract,
verification, report, and manifest byte.

## Readiness Handoff

The immutable prior readiness evidence was re-registered with only the formal
reward binding added.

- Readiness registration: `reports/noncombat_formal_rl_readiness_audit_20260802_r2_input.json`
- Readiness registration SHA-256: `17b7f03854ae96aa5d46eb9d684e8cd6d74c48185c30e4062abcda599a8e5e93`
- Canonical readiness directory: `reports/noncombat_formal_rl_readiness_audit_20260802_r2`
- Reward domain: `blocked -> passed`
- Unchanged passed domains: `state_action`, `reference_isolation`, `evaluation`
- Unchanged blocked domains: `baseline_policy`, `outcome_support`
- Overall verdict: `not_ready_for_bounded_training_proposal`

Every non-reward domain, prior evidence binding, analyzer identity, gate value,
and authority value remained identical. All gameplay, simulator rollout,
native loading, model fitting, formal RL, OPE reinterpretation, qualification,
live loading, and policy promotion authority remains false.

## Verification

- Formal reward focused tests: `16 passed`
- Formal readiness adjacent tests: `9 passed`
- Simulator smoke registration/reward tests: `9 passed, 18 deselected`
- Repository commit gate: `3298 passed, 11 skipped` in `287.81s`
- Strict OpenSpec validation: passed
- Global OpenSpec validation: `54 passed, 0 failed`
- Contract strict canonical recomputation: passed
- Readiness strict canonical recomputation: passed
- Reward-only matrix delta audit: passed

No gameplay, simulator rollout, native module, PyTorch model, model fitting,
training, OPE estimate, qualification, or live policy process was started.

## Next Boundary

Formal non-combat RL remains blocked. The next prerequisite is a separately
reviewed, non-teacher credible baseline-floor plan. It must begin with a
read-only inventory and contract rather than another imitation fit or an
unregistered simulator cohort. Target-supported outcome evidence remains a
separate later blocker.
