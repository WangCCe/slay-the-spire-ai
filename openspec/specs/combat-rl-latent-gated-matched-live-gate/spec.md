# combat-rl-latent-gated-matched-live-gate Specification

## Purpose

Define the source-bound, eval-only latent-gated candidate runtime and the
matched live evidence required before a candidate may be considered for a
separate promotion decision.

## Requirements

### Requirement: Source-bound candidate registration
The runtime SHALL enable latent-gated candidate takeover only from an explicit
committed `mode=candidate` registration that binds source, adapter artifact,
production-parent checkpoint, parent parameter state, trace destination, and a
finite decision budget.

#### Scenario: Candidate registration is valid
- **WHEN** eval mode loads a committed candidate registration whose source and artifact identities match the active checkout and production r16
- **THEN** the adapter is initialized against the frozen parent and candidate mode may become active

#### Scenario: Candidate registration differs
- **WHEN** mode, source, path, hash, parent state, trace boundary, or decision budget differs
- **THEN** initialization fails before candidate-controlled gameplay

### Requirement: Eval-only gated takeover
Candidate mode MUST require training disabled, epsilon exactly zero, expert mix
disabled, and a production-parent checkpoint. It SHALL select the legal adapter
action only when the gate is open and otherwise retain the frozen-parent action.

#### Scenario: Gate opens on a legal correction
- **WHEN** parent parity holds, the candidate action is legal, and the registered gate opens
- **THEN** RL v2 returns the candidate action as its proposal to the existing outer combat guards

#### Scenario: Gate remains closed
- **WHEN** the registered gate does not open
- **THEN** RL v2 returns the frozen-parent proposal unchanged

#### Scenario: Training or exploration is requested
- **WHEN** candidate mode is combined with training, nonzero epsilon, or expert mix
- **THEN** initialization fails before gameplay

### Requirement: Mutually exclusive latent live modes
Shadow observation and candidate takeover MUST NOT be active in the same RL v2
process, and the batch wrapper SHALL clear both registration variables unless
their corresponding explicit arguments are supplied.

#### Scenario: Both modes are configured
- **WHEN** both latent shadow and latent candidate registrations are present
- **THEN** agent initialization fails before gameplay

#### Scenario: No latent argument is supplied
- **WHEN** the batch wrapper launches an ordinary parent arm
- **THEN** ambient shadow and candidate registration variables are removed from the child environment

### Requirement: Candidate and final-action evidence
Each candidate proposal SHALL record parent parity, gate state, candidate
legality, selected proposal, takeover status, adapter latency, and the final
guarded action. Transient control actions SHALL be audited separately.

#### Scenario: Candidate proposal is committed
- **WHEN** outer guards emit a final encodable combat action
- **THEN** the trace records whether the selected candidate proposal matches the legal final action and advances one contiguous decision sequence

#### Scenario: Transient wait is emitted
- **WHEN** a stale-state refresh emits `WaitAction`
- **THEN** the pending proposal becomes a transient-discard event without consuming the candidate decision budget

#### Scenario: Candidate runtime fails
- **WHEN** proposal or commit processing raises, parent parity fails, or a candidate action is illegal
- **THEN** candidate takeover is disabled, an error or invalid decision is recorded, and the arm is ineligible even if gameplay continues under the parent

### Requirement: Preregistered matched gameplay cohort
The evaluation SHALL use exactly ten fresh Ironclad A0 seeds in identical order
for candidate and production-r16 parent arms, with conservative routing, eval
mode, epsilon zero, training disabled, and production restored between arms.

#### Scenario: Both arms complete
- **WHEN** candidate and parent each complete ten natural runs on the registered seed order
- **THEN** run records, logs, traces, seed identity, and configuration restoration are reconciled before scoring

#### Scenario: Execution boundary changes after start
- **WHEN** checkpoint, adapter, seed order, threshold, routing, or evaluation settings change after the first completed game
- **THEN** the gate is invalid and is not reinterpreted as matched evidence

### Requirement: Conservative qualification and promotion boundary
The candidate SHALL qualify only when it wins more paired floor comparisons
than r16, at least one pair differs, total floors and progression counts are
non-worse, victories are non-worse, both arms and all runtime checks complete,
and candidate takeover is observed. Passing SHALL NOT automatically promote it.

#### Scenario: Every registered condition passes
- **WHEN** the complete reconciled report satisfies every fixed technical and paired outcome condition
- **THEN** the candidate is eligible only for a separate promotion decision

#### Scenario: All pairs tie or any condition fails
- **WHEN** all floor pairs tie or any technical, completion, identity, progression, victory, or paired condition fails
- **THEN** production r16 remains authoritative and the cohort is closed to tuning or retry
