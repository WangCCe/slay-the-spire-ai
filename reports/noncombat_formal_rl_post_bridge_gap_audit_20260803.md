# Non-Combat Formal RL Post-Bridge Gap Audit

Date: 2026-08-03

## Decision

- Formal non-combat RL: `no_go`.
- Bounded-training proposal ready: `false`.
- New diagnostic, native cohort, gameplay, or training authorized: `false`.

The potion and relic repairs close the known static item-name hydration gaps in
the Current simulator bridge. They do not add a Current own-trajectory row,
demonstrate a credible non-teacher baseline floor, or add a source-comparable
target-supported victory. The formal readiness verdict therefore remains
`not_ready_for_bounded_training_proposal`.

## Bound Evidence

This audit binds only tracked evidence at repository commit
`386ef60525d275d3bd9493c1f77e5b479299e2bf`. The primary inputs are:

| Evidence | SHA-256 |
|---|---|
| `reports/noncombat_formal_rl_readiness_audit_20260802_r2/report.json` | `3458b0f27ab5ff65f60e280f010c2a9802e92ee6f0f71d530df2151be14da97a` |
| `reports/noncombat_baseline_floor_readiness_audit_20260803.json` | `1ffa837357acf4f93574ec9749f48e03cac26fb05dfe4d023f5aeb001011b621` |
| `reports/noncombat_study_feasibility_20260802.json` | `46d9321676676b92756caab5e35cddb4055086078accacb13e83540a81240bbe` |
| `reports/noncombat_current_bridge_diagnostic_smoke_20260803_closeout.md` | `006ffd7c3e3c662cc87fcd1f25550e3acc73ef61ca7912de533bc111ff0fed0f` |
| `reports/noncombat_current_bridge_diagnostic_smoke_20260803_r2_closeout.md` | `755b9d09f97aab66cb23bb4e9d5314e5fb934d22c44995a5b123e42e87aa8fc7` |
| `reports/noncombat_current_bridge_potion_metadata_identity_audit_20260803.md` | `f1d0dbe5ddb7ab20969ef2f349abf2515f39072b4575251849f6efcb5cc98494` |
| `reports/noncombat_current_bridge_card_relic_metadata_identity_audit_20260803.md` | `4835936675f0a6c131ac0dcead73d4d91773a8c9215574a2fb83c150a5379b1a` |

No untracked report was used as evidence. No native module, simulator
environment, seed, gameplay process, model, trainer, or external policy was
loaded or executed.

## Readiness Matrix

| Domain | Current status | Post-repair effect |
|---|---|---|
| State/action | `passed` | Unchanged |
| Reference isolation | `passed` | Unchanged |
| Reward | `passed` | Unchanged |
| Baseline policy | `blocked` | No new Current trajectory evidence |
| Outcome support | `blocked` | No new source-comparable outcome |
| Evaluation | `passed` | Unchanged |

The remaining blockers are exactly:

- `credible_baseline_floor_not_demonstrated`
- `target_supported_outcome_evidence_not_demonstrated`

## What The Repairs Prove

The frozen base-game item surface now has a closed compatibility account:

- Cards: all 370 audited native display names occur in metadata.
- Potions: 39 direct matches plus three stable-ID-bound aliases cover all 42
  non-empty native potions.
- Relics: 163 direct matches, 15 stable-ID-bound aliases, and the two exact
  simulator fallback exemptions cover all 180 non-invalid native identities.

The mappings fail closed on changed names, unknown IDs, and missing canonical
metadata. This is code-level structural evidence only. It does not prove that
all reachable snapshots hydrate, that Current completes a trajectory, or that
Current meets any policy-quality threshold.

## Why Baseline Policy Remains Blocked

Both registered Current diagnostics are consumed and retained zero rows:

1. The first stopped on the runner's invalid `action_type` assumption.
2. R2 stopped on `potion_metadata_missing` for `Elixir Potion`.

The later candidate-schema and item-identity repairs cannot reinterpret those
attempts. There is still no completed Current own-trajectory evidence and no
fixed comparison, absolute-quality, paired-quality, unsupported-rate,
bootstrap, stop, or untouched-holdout result establishing a baseline floor.
Preparing r3 or silently substituting another cohort would violate the frozen
anti-retry boundary.

## Why Outcome Support Remains Blocked

The feasibility evidence contains 125 historical complete trajectories, one
raw victory, and zero deterministic-Current-supported victories. Its source is
`historical_reference_only`, so it is not comparable to the target policy. The
plug-in probability of obtaining the registered three supported victories in
600 attempts is therefore zero. An 80% plug-in pass probability would require
an observed supported-victory rate of about 0.7118%, but the current evidence
cannot estimate that rate for Current.

Static bridge repairs add no outcome and do not change this blocker.

## Recommended Decision Sequence

Do not start formal non-combat RL training now. If the project continues this
RL line, first make an explicit decision to fund a separately reviewed OpenSpec
proposal for post-repair Current baseline evidence. That proposal must use a
new identity, untouched fixed cohort, exact comparison and quality gates,
unsupported-rate ceiling, replay/bootstrap/stop contracts, and untouched
holdout. Proposal approval must remain separate from execution approval.

Only after the baseline lane has credible signal should the project spend the
higher operational budget on source-comparable target-supported outcomes. That
second lane requires its own known-propensity evidence plan and cannot treat
Bottled, SimpleAgent, or historical raw victories as target-policy truth.

The alternative is to defer formal RL and return to bounded gameplay
maintenance. Until that direction is selected explicitly, stop at this audit:
do not prepare r3, access a cohort, launch gameplay, fit a model, or train.
