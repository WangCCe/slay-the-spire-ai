# Pytest Commit Gate Timing Invalidation - 2026-08-10

## Decision

The repository's `commit` profile remains correctness-green but its qualified
five-minute feedback claim is invalid. This entrypoint change does not modify
the test manifest, runner, pytest configuration, or `full_only` boundary, and
does not attempt requalification.

## Evidence

The last valid requalification passed 3,571 tests with 16 skips in 259.47
pytest seconds and 262.89 gate seconds. A later frozen successor-source run
already passed 3,895 tests with 16 skips in 511.96 pytest seconds and 515.35
gate seconds, exceeding the unchanged 300-second ceiling.

During this change, the first unchanged-profile invocation was interrupted by
the outer observer after 424.37 seconds and produced no pytest terminal. A
second unchanged-profile invocation used a longer observer window solely to
obtain the missing correctness terminal:

| Profile | Result | Pytest time | Gate time | Interpretation |
| --- | ---: | ---: | ---: | --- |
| `commit` | 3,918 passed, 16 skipped | 525.50s | 528.59s | Correctness green; timing invalid |

The second invocation did not change tests, selection, exclusions, or pytest
arguments and is not a timing requalification. Focused dispatch tests passed 5
nodes, the complete seed-inventory file passed 27 tests in 30.39 seconds, and
the existing control import-isolation node passed once.

## Attribution Boundary

Read-only Git comparison found no manifest, runner, or pytest-configuration
change since the last five-minute qualification. The dominant post-
qualification growth is in ordinary card-acceptance successor runtime,
verifier, control, and seed-inventory coverage. The current dispatch tests add
two short isolated interpreter processes but do not explain the pre-existing
515.35-second result.

No `full_only` entry is added or changed here. A later dedicated
requalification must freeze the post-qualification ordinary-file candidate set
before measurement, preserve the outcome without adaptive exclusion changes,
and state an honest feedback target if the inclusive profile remains above five
minutes.

## Applicability

Fresh gameplay validation is not applicable: this source-only entrypoint repair
does not alter production gameplay imports, CommunicationMod configuration,
policy behavior, checkpoints, native/model loading, training, evaluation,
qualification, or promotion. No inventory, seed, cohort, game, or
CommunicationMod operation was run by this timing audit.
