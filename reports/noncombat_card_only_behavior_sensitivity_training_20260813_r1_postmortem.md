# Card-Only Behavior Sensitivity Training r1 Postmortem

## Decision

The 16-step candidate-only continuation is not ready for fresh evaluation or
live loading. It completed the registered training and comparison, but failed
both the fixed behavior-change gate and the native-control floor gate.

Do not extend the same schedule, tune against this cohort, or promote
`checkpoint_020`. Native SimpleAgent remains the rollback policy.

## Execution

- Source commit: `197f79e632b080dd55594bd623a0652da5f27caf`.
- Registration SHA-256: `85b1cd0d671ce4251e3f6fac571e68cc211f13704e71521bdb59bdaadfd826bc`.
- Entry: the bound r7 `checkpoint_004`, including model, Adam moments, and RNG.
- Added optimizer steps: 16, for 20 total candidate steps.
- Training environment accesses: 1,024 candidate-only episodes.
- Terminal comparison accesses: 128, for 1,152 total.
- Wall time: 8,622 seconds, about 2 hours 24 minutes.
- Complete training support: 1,006 / 1,024 trajectories.
- Censored trajectories: 18, all from the declared Courier-restock blocker.
- Candidate card decisions used by training: 9,082.
- Training-trajectory victories: 3; these are exploratory sampled outcomes and
  are not promotion evidence.
- No game, CommunicationMod, protected cohort, or production checkpoint was
  accessed or changed. All downstream authority flags remained false.

## Behavior Result

The model moved substantially in parameter space but not in the registered
fixed-probe action space.

- Final parameter L2 distance from entry: `1.496854`.
- Fixed-probe exact-action flips: `0 / 175`.
- Fixed-probe family flips: `0 / 175`.
- Entry and final fixed-probe take rate: `0.537143`.
- Intermediate steps 6 through 16 produced one probe action/family flip, but
  steps 18 through 20 returned to zero flips.
- Family coverage never collapsed and therefore did not trigger the safety stop.

Parameter norm is therefore not a useful proxy for policy behavior in this
setup. The only observed fixed-probe boundary crossing was transient.

## Terminal Comparison

The corrected support-aware comparison attempted all 64 registered seeds and
evaluated 63 complete supported pairs after censoring seed 1014 for the declared
Courier blocker.

| Metric | Candidate | Native control | Check |
| --- | ---: | ---: | --- |
| Mean floor progress | 0.365636 | 0.376775 | Fail |
| Victories | 1 | 0 | Pass |
| Greedy multi-family take rate | 0.472222 | n/a | Pass |
| Fixed-probe action flips | 0 | minimum 4 | Fail |
| Supported pairs | 63 | 63 | Pass |

Verdict: `card_only_behavior_sensitivity_not_ready`.

The candidate-control floor difference was `-0.011139`. The single candidate
victory does not override the failed mean-floor and behavior gates on this
reused development cohort.

## Interpretation

The continuation answered the main mechanism question:

1. Candidate-only collection doubles useful optimizer steps per training
   environment budget relative to the paired r7 loop.
2. The gradient path, checkpoint ownership, support censoring, and resume
   boundary remain operational for 16 consecutive updates.
3. More steps with the same objective do not create a stable greedy policy
   change on the fixed probe and do not close the native floor gap.

The next bottleneck is not training throughput. It is the relationship between
the estimated advantage gradient and the policy function represented on
decision states.

## Next Work

Run a source-only, no-update function-space diagnostic over entry and final
checkpoints before proposing another training experiment:

1. Measure per-row family and conditional KL, action margin change, acceptance
   coordinate change, and how many rows approach but do not cross a greedy
   boundary.
2. Break those metrics down by take, skip, and bowl support and compare them
   with the recorded advantage and clipping distributions.
3. Determine whether the ineffective behavior comes from low functional
   movement, movement concentrated outside the fixed probe, saturated margins,
   or a weak/noisy advantage direction.
4. Only then propose one bounded change to advantage normalization, optimizer
   scaling, or representation. Do not change several at once.

No fresh seed or live-game budget is justified by r1.

## Evidence

- Terminal: `reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1/terminal.json`
  (`6023d29383a104eb1e74daea6247800f29a7b1ecc0dd2065a5f1dacb7ad4ac49`).
- Comparison: `reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1/comparison.json`
  (`1f680c636aa60d10fa4853cf1a61314ed11539aa9a1795ee6c0d36d55a7c90c1`).
- Report: `reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1/report.json`
  (`230ba279c43370249a74ffd158834b89517d0e58325e3bb6a2bcd667ebe5e302`).
- Final exploratory checkpoint: `reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1/checkpoint_020.json`
  (`d6d08932c5212df6a415c2f20291d2af94b27acdabbb5923451588f9eab50caf`).

Intermediate checkpoints remain local for audit and recovery but are not part
of the compact source-control evidence boundary.
