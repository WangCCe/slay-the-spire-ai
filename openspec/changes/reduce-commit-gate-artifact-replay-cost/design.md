## Context

The current `commit` profile passed 4,468 outcomes in 209.529 seconds. JUnit
attributes 189.568 seconds to tests and leaves 19.961 seconds to collection,
imports, and runner overhead, so runner micro-optimization cannot recover the
desired margin. The slowest individual tests are distributed; six bound
artifact-replay nodes total 24.832 seconds while their containing files retain
useful fast tests.

The manifest already supports fail-closed node-level `commit_deselect` entries.
The inclusive `full` profile and direct pytest ignore that list, and exact
manifest regressions freeze its content and measured aggregate.

## Goals / Non-Goals

**Goals:**

- Preserve every ordinary test in each affected file.
- Remove only six measured artifact-replay nodes from routine `commit` runs.
- Keep direct pytest, positive domain profiles, and `full` inclusive.
- Qualify one frozen boundary at no more than 190 runner seconds.
- State direct focused ownership for every new exclusion.

**Non-Goals:**

- Parallel pytest, xdist, persistent workers, caching, or subprocess pooling.
- Whole-file exclusions, test deletion, assertion changes, or automatic
  timing-based manifest mutation.
- Production AI, simulator, gameplay, native, model, or training changes.
- A second qualification after a slow or failed frozen result.

## Decisions

Add exactly these six node-level entries, ordered by the existing timing report:

| Node | Seconds | Direct ownership |
| --- | ---: | --- |
| `tests/test_combat_rl_real_context_weighted_action_relative_fit.py::test_bound_train_parity_split_has_registered_rows_and_weight_support` | 8.080 | `analysis_scripts/combat_rl_real_context_weighted_action_relative_fit.py` and its bound real-replay/corpus inputs |
| `tests/test_noncombat_event_ranker_paired_trajectory_shadow.py::test_bound_training_support_restores_manifest_dataset` | 4.815 | `analysis_scripts/noncombat_event_ranker_paired_trajectory_shadow.py` and its bound training manifest |
| `tests/test_combat_lightspeed_checkpoint_interpolation.py::test_publication_is_bound_deterministic_and_comparator_compatible` | 4.012 | checkpoint interpolation publication plus the candidate/checkpoint helpers exercised by the node |
| `tests/test_noncombat_ope_estimate_artifacts.py::test_estimate_writer_is_transactional_and_cli_uses_explicit_outputs` | 3.225 | OPE estimate artifact writer and CLI |
| `tests/test_noncombat_ope_estimate_artifacts.py::test_estimate_artifact_is_deterministic_hash_bound_and_gate_separated` | 2.889 | OPE estimate artifact builder and estimator-bundle binding |
| `tests/test_noncombat_ope_estimate_artifacts.py::test_estimate_renderers_are_byte_stable_and_make_no_downstream_claim` | 1.811 | OPE estimate JSON and Markdown renderers |

Use node-level deselection for all six. Whole-file exclusion of the 11.959-second
OPE file was considered and rejected because its remaining six tests are cheap
and useful in routine commits. The 4.546-second static event-semantics node is
not selected because it is ordinary behavioral coverage rather than historical
artifact replay.

Extend the exact repository-manifest regression with the six node IDs and
their measured durations. The expected excluded aggregate becomes 128.481
seconds. Existing command-construction regressions remain the proof that only
`commit` emits deselections; a repository dry-run records unchanged inclusive
`full` arguments.

Run each new node directly once as the focused ownership baseline, then run the
runner regression and strict OpenSpec validation. Freeze and commit that exact
manifest before one timing-enabled `commit` qualification. The expected wall
time is 184.697 seconds before load variance; acceptance remains the stricter
190-second target recorded in the proposal.

## Risks / Trade-offs

- [Risk] A routine commit can break excluded artifact integration. -> Require
  the owning node directly whenever its test, source, bound artifact schema, or
  executable helper changes; retain it in `full` and positive domain profiles.
- [Risk] The 190-second target may fail under normal variance. -> Preserve the
  exact result, do not retry or add exclusions, and roll back the six entries as
  one boundary.
- [Risk] Exact manifest totals can drift after a rename. -> A stale deselection
  restores coverage and consumes time; the exact-manifest regression exposes
  the mismatch before qualification.
- [Risk] More exclusions gradually hollow out commit coverage. -> Keep the
  candidate set frozen to six and require a separate measured OpenSpec change
  for any later entry.

## Migration Plan

1. Add RED exact-manifest expectations for the six frozen candidates.
2. Add the six manifest entries and focused-ownership documentation.
3. Run all six nodes directly, runner-focused pytest, strict OpenSpec
   validation, and commit the frozen selection.
4. Prove `full` dry-run remains inclusive and run one timed `commit`
   qualification.
5. If qualification is green and at most 190 seconds, publish timing evidence;
   otherwise preserve the result and revert the six entries together without a
   second qualification.

## Open Questions

None. The candidate set, ownership, target, and rollback boundary are frozen.
