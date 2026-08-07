# Cross-Fitted Hierarchical Learning Terminal Postmortem

## Decision

The single authorized logical execution is closed and independently valid as
`experiment_failed_after_seed_access`. It is a preserved post-start failure,
not a valid completion, family-saturation result, or pre-start block. The
failure is terminal because the runner's registered wall-time gate fired after
seed access and classified the cause as non-infrastructure. No resume or retry
is authorized.

The run produced no complete chunk, fitted baseline, retained decision bundle,
optimizer update, checkpoint, gradient evidence, or policy-quality evidence.
Formal non-combat RL, another experiment, model loading, gameplay,
CommunicationMod, qualification, and promotion remain `no_go`.

## Verified Terminal Bundle

The independent standard-library verifier accepted the closed manifest,
terminal identity, approval and authorization bindings, access journal,
resource ledger, pre/post isolation observations, and all 13 managed artifacts.
It reported:

- verdict `experiment_failed_after_seed_access`;
- 12 debited environment accesses;
- 0 completed chunks, optimizer updates, checkpoints, or retained decisions;
- no resume mode and `resume_used=false`; and
- terminal SHA-256
  `1887395ae2e4e23d031a3370695e6f694b6ba079ba8b110ceb36b34642e452d8`.

The access journal contains 25 events under attempt ordinal `0`. Seeds
`1769..1780` were debited in schedule order. Eleven accesses completed. The
twelfth debit, seed `1780`, was closed as failed before its environment was
constructed because the deadline had already been crossed.

| Evidence | Count |
| --- | ---: |
| Scheduled seeds | 512 |
| Debited accesses | 12 |
| Completed accesses | 11 |
| Failed accesses | 1 |
| Completed chunks | 0 |
| Optimizer updates | 0 |
| Checkpoints | 0 |
| Retained decisions | 0 |

## Wall-Time And Accounting

The runtime's own fixed deadline check raised
`wall-time limit reached before environment construction` at the registered
14,400-second ceiling. The terminal resource ledger nevertheless reports
`charged_seconds=0.0`. This does not mean the execution consumed zero time.
The current implementation persists elapsed charged time at a complete
checkpoint or for an infrastructure interruption; this non-infrastructure
failure occurred before the first checkpoint, so its terminal ledger retained
the zero origin while access debits advanced to 12.

Filesystem timestamps are noncanonical operational observations, but they
show the scale of the control-plane path:

| Observation | Local time | Delta |
| --- | --- | ---: |
| Lease acquired | 2026-08-07 11:09:44 +08:00 | - |
| Failure witness | 2026-08-07 15:33:18 +08:00 | 15,813.526 s from lease |
| Terminal intent | 2026-08-07 15:48:40 +08:00 | 922.078 s after failure |
| Terminal document | 2026-08-07 16:09:59 +08:00 | 1,279.142 s after intent |
| Manifest | 2026-08-07 16:10:26 +08:00 | 27.000 s after terminal |

The evidence cannot attribute the pre-failure duration solely to the native
simulator. It includes episode work and repeated control-plane validation,
journal, resource, hashing, and publication paths. A separate read-only source
and artifact audit must decompose those costs before any repair or new run is
proposed.

## Monitoring Deviation

The outer command wrapper returned exit code `124` at its five-hour timeout,
but it had stopped waiting without terminating the Python child. I initially
treated that wrapper result as process exit and read small control files below
the output root. The first verifier attempt failed closed because the live
lease was still locked. Process inspection then confirmed the original Python
PID remained alive.

No artifact was modified, no signal was sent to the experiment, and no second
execution was started. Monitoring immediately returned to liveness only until
the original PID exited naturally. The verifier was rerun only after that exit
and accepted the final immutable bundle. This procedural deviation is recorded
because the active-root rule was not followed perfectly even though artifact
integrity and execution identity remained intact.

## Isolation And Publication

Both isolation observations match registration. The CommunicationMod config
hash is unchanged, and all 208 production checkpoint files totaling
1,356,047,034 bytes retain the registered identity. Slay the Spire and
CommunicationMod were not launched, and no production checkpoint was loaded or
modified.

The complete canonical terminal bundle is preserved under
`reports/noncombat_cross_fitted_hierarchical_learning_successor_20260806_r1`.
Its manifest binds 13 managed artifacts and 63,920,322 stored bytes. Ordinary
Git publication includes the managed bundle and omits only the inactive
`.execution.lease` control file.

## Next Gate

Do not resume, replay, tune, replace seeds, or start a successor experiment.
The next work is a separate read-only terminal execution-bottleneck audit. It
must distinguish native episode time from registration validation, access
journal/resource reconciliation, hashing, isolation observation, and terminal
publication costs; it must also account for non-infrastructure elapsed time in
future terminal ledgers.

Only a source-only repair proposal with RED lifecycle/performance regressions
may follow that audit. Any later evidence-bearing execution requires a new
identity, fresh registration and cohort decision, and separate exact human
authorization. This closeout establishes no policy quality, causal effect,
formal RL readiness, target-supported outcome, live value, qualification, or
promotion eligibility.
