# Known-Propensity Exploration Independent Review - 2026-07-14

## Scope

This review closes OpenSpec change
`add-known-propensity-noncombat-exploration`. It covers the implementation,
the 25-run B1 evidence package, accepted review fixes, and the post-fix R6 live
smoke. Formal non-combat RL, OPE, causal uplift, and live promotion remain out
of scope and blocked.

## Findings And Resolutions

1. **Raw B1 log claims were not independently reproducible.** The original
   package preserved counts and excerpts but not the complete bounded slices.
   Commit `830e376a` added deterministic AI-debug and CommunicationMod slices,
   source ranges, payload hashes, and diagnostics. Independent re-review
   rebuilt the available source segments and reported no remaining finding.

2. **Alternative actions retained Current callback side effects.** Card-reward
   alternatives could retain baseline tracker and decision-history updates;
   shop alternatives could retain purchase or purge state. Commit `830e376a`
   added action-scoped preview, rollback, and selected-arm commit behavior for
   SimpleAgent and CombatRL, including deferred final decision tracing.

3. **Properties hashing did not model duplicate-key semantics.** Commit
   `830e376a` changed isolation hashing to an effective Java Properties mapping
   with escape, continuation, and last-value-wins behavior.

4. **Replay accepted coercible exact fields.** Commit `830e376a` made draw,
   decision-index, and probability integers reject strings, floats, and bools.

5. **Python natural-line parsing was broader than Java.** Independent
   re-review found that `splitlines()` also split FF, VT, and NEL characters.
   Commit `1a5d47f1` now splits only CR, LF, and CRLF and preserves other
   control characters inside property values.

6. **Alternative-budget history still accepted float/bool equality.** Commit
   `1a5d47f1` requires exact non-boolean integers for both `limit` and
   `used_before`.

The final narrow code re-review reported no findings. The final R6 raw-evidence
review also reported no findings.

## B1 Disposition

B1 remains valid diagnostic evidence for persistence, replay, confirmation,
run joining, support accounting, and log reconstruction. It is not admissible
as policy-training, OPE, causal, or promotion evidence: its source commit ran
before selected-arm side-effect isolation, so all 20 card-reward and 4 shop
alternative rows may have affected later policy state in their trajectories.

The B1 sample rows themselves retain their historical
`confirmed_known_propensity` field. Consumers must therefore use the B1 report,
qualification flags, and this session-level quarantine rather than ingesting
that JSONL in isolation.

## Post-Fix Live Evidence

R6 ran from source commit `830e376a` with no training, 10 percent category
rates, and a two-attempt per-run budget. Its completed trajectory selected and
confirmed both repaired alternatives:

- Shop floor 2: final `LeaveAction`; no purchase or purge in the run.
- Card reward floor 10: final `CancelAction`; no baseline `Anger` in the deck.

All eight R6 proposal/resolution pairs replay and confirm. Four samples from
the completed trajectory match its exact run; four samples from the interrupted
next trajectory remain `join_status=missing`. Isolation and source provenance
both verify. Independent review recomputed all 19 report hashes and rebuilt the
two selected-action rows from the original 2.08 GB decision trace.

R6 proves the repaired routing, confirmation, and externally visible state. It
does not qualify the data loop or establish policy quality or outcome uplift.

## Verification

- Review regressions: `6 failed` before the final two fixes, then `71 passed`.
- Final focused exploration/runtime/export suite: `330 passed`.
- Final full pytest suite: `2527 passed`.
- `openspec validate add-known-propensity-noncombat-exploration --strict`:
  passed.
- `git diff --check`: passed.
- Remaining game, ModTheSpire, and AI processes after R6: none.

## Residual Risks

- B1 quarantine is session/report level rather than embedded in each historical
  sample row.
- Transaction unit tests use synthetic callbacks; R6 supplies the real
  CombatRL/OptimizedAgent live-path evidence for the two executable alternatives.
- R6 repeated the recoverable stale `start` startup error and began a second
  trajectory before controlled shutdown; both limitations are frozen and do
  not contribute matched outcome support.
- Standalone-CR Properties input and `limit=true` are not separate committed
  exporter cases, but direct review probes passed and the shared strict parser
  and integer helper cover those paths.

## Decision

The change is complete as a bounded known-propensity data-collection loop.
`known_propensity_exploration_data_ready`, `ope_ready`, `causal_uplift_ready`,
`formal_noncombat_rl_training_ready`, and `live_policy_promotion_ready` remain
false. Any attempt to qualify a new batch must start from the post-review code
and fresh trajectories; B1 cannot be promoted retroactively.
