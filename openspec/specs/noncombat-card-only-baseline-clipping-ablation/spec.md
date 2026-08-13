## Purpose

Define a bounded shared-trajectory mechanism experiment that isolates the effect
of baseline prediction clipping on one card-policy optimizer step without
granting downstream training, evaluation, gameplay, loading, or promotion
authority.

## Requirements

### Requirement: One shared candidate trajectory cohort feeds both branches
The ablation SHALL restore exact checkpoint `004` and collect exactly one
registered 64-seed candidate-only consumed-development cohort for both updates.

#### Scenario: Shared cohort is valid
- **WHEN** 56 to 64 trajectories remain after known bounded Courier censoring
- **THEN** both branches use the same ordered states, candidates, selected actions, rewards, returns, and held-out baseline models
- **AND** the experiment charges 64 environment accesses total

#### Scenario: Shared cohort is invalid
- **WHEN** an unknown blocker occurs, more than eight trajectories are censored, or fewer than 56 remain
- **THEN** neither optimizer step is published
- **AND** no seed is replaced or replayed under the same experiment identity

### Requirement: Baseline clipping is the only branch difference
Branch A SHALL use each held-out prediction clipped to `[0, 3]`, while branch B
SHALL use the corresponding finite pre-clip prediction with fixed unit scale.

#### Scenario: Branch terms are constructed
- **WHEN** shared trajectories and the cross-fitted baseline validate
- **THEN** branch B recomputes policy terms on its own checkpoint `004` model for the exact stored candidate order and selected action
- **AND** raw returns, ridge models, Adam state, entropy coefficient, learning rate, gradient ceiling, and every other policy input are equal between branches

#### Scenario: Branch ownership differs
- **WHEN** a policy term or optimizer parameter is not owned by its exact branch model
- **THEN** both branches restore checkpoint `004`
- **AND** no partial model or result is published

### Requirement: Current semantics reproduce the historical next checkpoint
The ablation SHALL compare branch A candidate model bytes after its single step
with the candidate model bytes in the bound r1 checkpoint `005`.

#### Scenario: Reproduction succeeds
- **WHEN** branch A model bytes exactly equal checkpoint `005`
- **THEN** branch B telemetry may be interpreted as a clipping ablation

#### Scenario: Reproduction fails
- **WHEN** branch A model bytes differ from checkpoint `005`
- **THEN** the verdict is `baseline_clipping_ablation_reproduction_failed`
- **AND** no mechanism or continuation claim is made

### Requirement: Compact branch telemetry is durable
The runner SHALL persist branch-local advantage, objective, gradient, parameter,
and fixed-probe function-space evidence without serializing full gradients or
trajectory payloads.

#### Scenario: Both updates complete
- **WHEN** branch A reproduces and branch B completes one step
- **THEN** the report includes clipped counts/ranges, advantage summaries, objective components, pre/post-clip gradient norms, applied-gradient cosine, parameter distances, probe action/family differences, KL, total variation, margins, model hashes, and input bindings
- **AND** all metrics are computed before trajectory tensors are released

### Requirement: Progression authority remains mechanism-only
The ablation SHALL stop after one optimizer step per branch and SHALL deny
fresh-evaluation, gameplay, policy-quality, production-loading, promotion, and
further-training authority.

#### Scenario: Material function or gradient effect is observed
- **WHEN** support, isolation, ownership, and reproduction pass, neither branch collapses, and the branches have an exact probe action difference, mean joint total variation at least `0.001`, or applied-gradient cosine at most `0.99`
- **THEN** the verdict is `ready_to_propose_four_step_baseline_clipping_ablation`
- **AND** no four-step run starts under this change

#### Scenario: Material effect is not observed
- **WHEN** all validity checks pass but none of the material-effect conditions hold
- **THEN** the verdict is `baseline_clipping_not_material_in_one_step`
- **AND** the same clipping ablation is not extended on this cohort
