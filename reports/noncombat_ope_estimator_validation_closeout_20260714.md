# Non-combat OPE estimator validation closeout (B3-B7)

Date: 2026-07-14
OpenSpec change: `add-noncombat-ope-estimator-validation`

## Decision

The estimator and the frozen B3-B7 dataset are ready for a reproducible offline
OPE estimate. The resulting Current-policy comparison is not ready and does not
support policy superiority, causal uplift, formal non-combat RL training, or live
promotion.

| Gate | Result |
| --- | --- |
| estimator validation | PASS |
| dataset estimation | PASS |
| OPE estimate | PASS |
| policy comparison | BLOCKED |
| causal uplift | BLOCKED |
| formal non-combat RL training | BLOCKED |
| live policy promotion | BLOCKED |

No gameplay policy, launcher default, run record, checkpoint, or live process was
changed or started by this change.

## Frozen provenance

| Input or implementation | SHA-256 |
| --- | --- |
| B3-B7 sample pool | `aa61da25c93cdfa24ec57f787fbd41b5e4921c1a1a2bf9cb75f799133159b292` |
| deterministic Current target | `f4cdce84382ed09747943594d140649700e5a98c9a05a3829c3d782410b0de8e` |
| deterministic readiness audit | `29fbd3543f718c34a626a27e1fad90b92465de4a53f30ef3f726002eca09abb8` |
| calibration artifact | `a7ac2ca9c2a0644125323769c6fcf6225295d4d6ec903995a5d332300a0eaf3f` |
| estimator implementation | `39e4b981348918ec8ab3e18c23f62f261be6a905d4b4c9826cfc3cae7e8bf370` |
| calibration implementation | `ff150e326932d5130b99e4fcb97ff9c285e0a9688938c1db3c618a53afb602c6` |
| estimate artifact implementation | `2486b7589b221193059e615ff3a6c5aa4573cd5017e800adfec8f51e9a52b98e` |
| independent verifier implementation | `de0e85eca294725adc9553e7870528f69777f248a39630891e253c39a1e52991` |
| final estimate artifact | `e5220f3c10000a4c68366d0084fd85d2b5713a46e4bff76298351bf74234386d` |

The estimate artifact binds the exact sample, target, readiness, calibration,
estimator, and renderer bytes. The independent audits bind the verifier bytes.

## Synthetic calibration

The fixed production calibration used 200 deterministic datasets, 200 complete
trajectories per dataset, and 500 whole-trajectory bootstrap replicates per
dataset.

| Metric | Result | Required |
| --- | --- | --- |
| SNIS target coverage | `193/200 = 0.965` | `[0.90, 0.99]` |
| SNIS uplift coverage | `191/200 = 0.955` | `[0.90, 0.99]` |
| target mean bias | `0.0016027424956265555` | absolute value at most `0.02` |
| uplift mean bias | `0.0012777424956265555` | absolute value at most `0.02` |
| undefined datasets | `0` | `0` |

The independent calibration replay passed 8,523 checks across all 200 datasets,
including exact fixtures, deterministic draws, interval endpoints, coverage,
bias, hashes, and downstream false gates.

## B3-B7 estimate

| Accounting | Value |
| --- | --- |
| complete trajectories | `125` |
| logged decisions | `1,253` |
| nonzero Current weights | `87` |
| zero Current weights | `38` |
| observed victories | `1` |
| effective sample size | `66.30163129572709` |
| ESS fraction | `0.5304130503658168` |
| maximum normalized weight | `0.04454188774597002` |
| production bootstrap replicates | `10,000` |
| zero-victory bootstrap replicates | `3,644` |
| undefined bootstrap replicates | `0` |

### Victory channel

| Estimate | Exact value | Display value |
| --- | --- | --- |
| logged behavior value | `1/125` | `0.008` |
| Current OIS value | `0/1` | `0.0` |
| Current SNIS value | `0/1` | `0.0` |
| Current-minus-behavior OIS | `-1/125` | `-0.008` |
| Current-minus-behavior SNIS | `-1/125` | `-0.008` |
| paired 95% SNIS uplift interval | `[-3/125, 0/1]` | `[-0.024, 0.0]` |

The only victory, trajectory `run:1784019948`, has 20 logged decisions and exact
Current trajectory weight `0/1`. Therefore the observed win contributes to the
behavior value but cannot support the deterministic Current target value.

The pre-specified policy-comparison blockers are:

- `leave_one_out_victory_snis_not_positive`
- `primary_victory_snis_interval_not_positive`
- `victory_ordinary_uplift_not_positive`
- `victory_self_normalized_uplift_not_positive`

Floor reached remains a secondary diagnostic and does not replace the failed
victory comparison.

## Independent replay and tests

- Final estimate replay: PASS, 1,268,818 checks, 10,000 replicates, full
  calibration replay, 125 trajectories, and 1,253 decisions.
- Focused estimator/calibration/verifier tests: `46 passed in 47.10s`.
- Full Windows pytest: `2,618 passed in 125.42s`.
- OpenSpec strict validation: PASS.
- Git whitespace check: PASS.
- Git index-versus-working-byte check for all hash-bound sources and artifacts:
  PASS for all 10 checked files.

The completion review found one audit-provenance issue: estimate verification
audits did not record the verifier implementation hash even though calibration
audits did. A red regression reproduced the missing field, the audit was fixed,
and both audit types were regenerated against the final verifier. No remaining
Critical or Important review finding was identified.

## Live isolation

The finalization window started with no `SlayTheSpire`, Java, or Python game
process. The live CommunicationMod command uses the Windows production Python to
run `scripts/run_training_batch.py --eval`; it does not contain `--train`.

The before snapshot covered the CommunicationMod configuration plus 208
checkpoint files (209 paths and 1,356,047,034 checkpoint bytes):

- snapshot SHA-256: `fb0a68e20e00284ef6b3a72be7f2bd726cd365dcbc11bf8f06e8b4c967f77c4b`
- config SHA-256: `374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a`
- config semantic SHA-256: `7341f96c64a633ed3b037ef499dd5b81c3355400c28c0f74c2afb6e83b9bdf51`
- after snapshot SHA-256: `fb0a68e20e00284ef6b3a72be7f2bd726cd365dcbc11bf8f06e8b4c967f77c4b`

A static regression parses `main.py` and every Python module under `spirecomm/`
and rejects imports of the estimator, calibration, estimate renderer, or
independent verifier. The final change list contains only offline analysis,
tests, OpenSpec bookkeeping, and reports. This same-session before/after check is
the isolation claim for this change; it does not claim byte identity with older
R4 exploration snapshots.

## Residual risks

1. One observed victory is not enough to resolve a victory comparison, and that
   sole winning trajectory has zero support under deterministic Current.
2. The 3,644 zero-victory bootstrap replicates make the primary interval discrete
   and uninformative even though the estimator itself is defined.
3. SNIS remains finite-sample biased. The calibration, OIS companion estimate,
   ESS, and leave-one-out diagnostics constrain interpretation but do not create
   causal evidence.
4. The proof of concept evaluates one frozen deterministic target. It does not
   establish a learned-policy objective, reward model, or promotion rule.

## Next gate

The next change should be an evidence-expansion gate, not formal RL training or a
gameplay policy edit. It should pre-register a bounded known-propensity collection
plan and its acceptance criteria before collecting more runs. The immediate
evidence objective is multiple complete-run victories with nonzero support under
the frozen candidate target while preserving exact propensities, complete
terminal outcomes, overlap checks, and independent replay.

After that frozen evidence passes readiness, rerun the same OPE and pre-specified
comparison gates. Only a separately proposed policy-learning change may define
how an accepted comparison affects rewards, training, candidate selection, or
live promotion. This report deliberately does not invent a post-hoc victory-count
or promotion threshold from the current result.
