## Context

The B3-B7 known-propensity pool proved that exact behavior probabilities, complete trajectory joins, deterministic Current target weights, overlap diagnostics, and the validated OPE estimator can all be reproduced independently. Its 125 trajectories and 1,253 decisions pass the existing structural and estimator gates, but the only victory has exact deterministic-Current weight zero. The primary victory comparison is therefore uninformative despite an ESS of 66.30 and an ESS fraction of 0.53.

The next experiment must increase independent terminal-outcome evidence without adapting to observed outcomes. Existing collection runs at about 25 games per hour and already has a hard 10 percent per-category exploration ceiling, a two-alternative-attempt per-run limit, and executable alternatives restricted to `card_reward:skip` and `shop:leave`. The experiment must use the Windows production Python, preserve CommunicationMod and checkpoint isolation, and remain separate from training or gameplay-policy development.

## Goals / Non-Goals

**Goals:**

- Commit an auditable study definition before any study run starts.
- Schedule at most 600 attempts as 24 immutable 25-run slots with one behavior regime.
- Preserve exact per-session propensity, transition-confirmation, run-join, source, and isolation evidence.
- Prevent outcome-dependent stopping, extension, rate changes, source changes, or selective session pooling.
- Produce a blinded structural monitor during collection and deterministic final evidence, target, readiness, estimate, and verification artifacts after unblinding.
- Require at least three distinct deterministic-Current-supported victories before calling the outcome-evidence expansion ready.

**Non-Goals:**

- No formal non-combat RL, reward shaping, policy gradient, Q-learning, model training, or checkpoint writes.
- No change to the frozen OPE estimator, 10,000-replicate production bootstrap, influence diagnostics, or policy-comparison conditions.
- No richer card, shop, event, or route alternatives and no Bottled policy in live action selection.
- No guarantee that 600 attempts will pass the evidence gate or produce a favorable policy comparison.
- No post-hoc replacement sessions, threshold relaxation, additional attempts, or mixing of data collected from different source locks.

## Decisions

### Commit a registration, then create a source-bound run lock

A versioned registration JSON is committed with the implementation before collection. It contains the study ID, schema, exact 24-slot schedule, deterministic seeds and session IDs, fixed command contract, behavior rates, alternative budget, output naming rules, integrity rules, final evidence thresholds, and hashes of all registration-controlled values. It intentionally does not contain the Git commit that contains itself.

Immediately before the first slot, a start command requires a tracked-clean tree and creates an immutable run lock. The lock binds the registration file bytes and canonical hash to the actual clean HEAD, hash-bound collection and analysis implementations, Windows Python path, exact child command, CommunicationMod semantic configuration, and checkpoint isolation snapshot. Every slot config and manifest references the same run-lock hash. A later source, registration, command, configuration, or checkpoint mismatch is a global integrity stop.

This two-stage binding avoids an impossible self-referential commit field while still proving that the registered rules predate all study outcomes.

Alternative: generate an untracked registration immediately before play. Rejected because its rules would not be durably reviewable before data collection.

Alternative: commit a file containing its own expected commit. Rejected because updating that value changes the commit recursively.

### Use one fixed behavior regime for all 24 slots

Every slot runs the equivalent of:

```text
D:\anaconda\envs\stsai\python.exe main.py --agent combat_rl --elite-route conservative --max-games 25 --ascension 0 --rl-version v2 --eval
```

through the existing bounded runner with an explicit exploration config. The config uses `card_reward=300` basis points, `shop=1000` basis points, and a per-run alternative budget of two. The lower card-reward rate preserves more deterministic-Current-supported trajectories across the many card decisions in a run; the 10 percent shop rate is needed because shop proposals are much rarer and rates below 10 percent produced zero to three shop alternatives per 25-run batch in B4-B7.

The 24 session IDs, seeds, trace paths, and manifest paths are derived from and checked against the committed slot table. No slot may change rates or command fields. Event and route records remain shadow-only.

The run-lock window also freezes repository bookkeeping. From run-lock creation through final artifact verification and the post-study isolation snapshot, no tracked file may change, including OpenSpec task checkboxes. Live progress is recorded only in the append-only study ledger outside the tracked source tree. Completed live tasks are checked off after the locked window closes.

Alternative: split the study into high- and low-exploration phases. Rejected because it creates unnecessary behavior-policy heterogeneity in the outcome-expansion dataset.

### Treat the schedule as an upper bound with no replacement slots

There are exactly 24 registered slots and each can launch at most once. A normally completed slot contributes up to 25 complete trajectories. A process that exits early is terminally marked `interrupted`; it is not restarted and its missing games are not replaced. The runner may continue to the next already registered slot only when the interruption is operational rather than a global integrity failure.

Successful evidence expansion requires at least 575 complete uniquely joined trajectories, allowing at most one 25-run slot of operational loss. The final artifact accounts for every slot as completed, interrupted, or globally blocked and includes every structurally eligible trajectory from every launched slot. There is no success-based early stop and no attempt extension after slot 24.

Alternative: keep launching replacement slots until 600 complete trajectories exist. Rejected because replacements chosen after observing collection progress weaken the fixed design and can hide operational exclusions.

### Expose only a blinded structural monitor during collection

The collection controller writes an append-only study ledger and offers a monitor command. Before all 24 slots are terminal, monitor output is limited to registration and run-lock validity, slot lifecycle, process exit, artifact existence, manifest/config hashes, exact replay and confirmation counts, conservative run-join completeness, and isolation status.

The blinded monitor must not emit or persist victory values or counts, floor reached, killed-by values, target weights, ESS, OPE estimates, bootstrap results, influence results, or comparison gates. Raw game files remain source evidence, but the supported workflow does not inspect their outcome fields. Operational diagnosis may inspect a stuck or failed process, but observed outcomes cannot change the schedule, rates, thresholds, source, or continuation rule.

Finalization is enabled only after all registered slots are terminal or after a global integrity stop. An integrity stop may be closed out immediately as blocked; it cannot be unblocked by additional collection.

Alternative: calculate the full pool after every slot and merely promise not to act on it. Rejected because a purpose-built redacted monitor makes accidental optional stopping less likely and testable.

### Build one deterministic all-slot pool at unblinding

Finalization enumerates the registration slot table rather than accepting an operator-provided allowlist. It verifies each slot's config, run lock, session manifest, append-only trace, confirmation joins, canonical samples, and run joins, then writes one pool manifest containing included and excluded sessions and trajectories with reasons. Input order cannot change the canonical pool bytes or qualification result.

Aggregate support is evaluated across the complete registered pool rather than requiring each 25-run operational slot to realize 50 alternatives. Included evidence must be 100 percent replay-valid, candidate-legal, transition-confirmed, and provenance-consistent. Each of `card_reward` and `shop` must contain at least 50 confirmed baseline and 50 confirmed alternative decisions.

The pool builder fails closed on a missing launched session, duplicate trajectory, unregistered session, source-lock mismatch, selective omission, conflicting run outcome, or artifact hash mismatch.

### Add a study-specific outcome-evidence gate above existing OPE readiness

After canonical pooling, finalization builds the deterministic Current target manifest using the existing exact target-policy implementation and runs the existing readiness and estimator pipelines unchanged. A separate `outcome_evidence_expansion_ready` gate requires all of the following:

- all 24 registered slots are accounted for and no global integrity stop occurred;
- at least 575 complete uniquely joined trajectories;
- at least 50 confirmed baseline and 50 confirmed alternative decisions in each executable category;
- deterministic-Current nonzero-weight trajectories are at least half of complete trajectories;
- deterministic-Current ESS fraction is at least 0.5;
- maximum normalized deterministic-Current weight is at most 0.05; and
- at least three distinct complete victory trajectories have deterministic-Current weight greater than zero.

These conditions qualify only the expanded evidence. The existing estimator-validation, estimate, bootstrap, influence, and policy-comparison gates are reported independently and are not weakened. Floor reached remains diagnostic. Passing any offline gate leaves causal uplift, formal training, reward design, and live promotion false.

Alternative: make policy-comparison success the collection acceptance criterion. Rejected because the purpose of collection is adequate pre-specified evidence, not a guaranteed favorable result.

### Independently verify registration through closeout

A standalone verifier re-reads the committed registration, run lock, slot ledger, session manifests, traces, pool, target, readiness, estimate, and closeout artifacts. It independently recomputes canonical hashes, slot completeness, inclusion accounting, exact support counts, deterministic-Current positive weights, ESS screens, supported victories, and downstream readiness booleans. The verifier must not import the study builder or finalizer implementation.

The closeout records verifier implementation hashes and same-session before/after CommunicationMod and checkpoint isolation snapshots. Any changed source byte, registration rule, pool membership, outcome, target probability, estimate, or gate boolean must invalidate verification.

## Risks / Trade-offs

- **The study still produces fewer than three supported victories** -> Close out as inconclusive at the registered limit; do not extend or lower the gate. Use that result to reconsider baseline win rate before proposing another OPE or RL stage.
- **A 10 percent shop leave rate harms outcomes** -> Keep it because overlap is the experiment's purpose and its rate is pre-registered; report the observed result without adapting the regime.
- **One interrupted slot leaves fewer than 600 trajectories** -> Permit at most one slot of loss through the 575-trajectory minimum; never launch replacement slots.
- **Structural monitoring accidentally reveals outcomes** -> Test the monitor schema and rendered output against an explicit forbidden-field set and keep finalization locked until all slots are terminal.
- **A gameplay or instrumentation bug appears mid-study** -> Record a global integrity stop, preserve all evidence, fix under a separate change, and require a new registration before collecting comparable data.
- **Long-running collection changes local live state** -> Require pre/post semantic CommunicationMod and checkpoint snapshots plus per-slot run-lock checks; stop on drift.
- **Passing the evidence gate is mistaken for policy approval** -> Keep outcome evidence, OPE estimate, policy comparison, formal training, and live promotion as separate fail-closed booleans.

## Migration Plan

1. Add registration, run-lock, schedule, ledger, blinded-monitor, finalization, and independent-verification tests before implementation.
2. Implement the offline study core and runner integration without changing the default gameplay path.
3. Generate the exact registration and 24-slot schedule, run focused and full tests plus strict OpenSpec validation, and commit all implementation and registration bytes.
4. From a tracked-clean source, create the run lock and perform a no-game dry run that validates all 24 commands, configs, paths, and forbidden training flags.
5. Capture the pre-study live isolation snapshot, finish and commit pre-lock bookkeeping, then create the run lock from a tracked-clean source.
6. Without editing any tracked file or OpenSpec checkbox, execute registered slots in order and run only the blinded monitor between slots.
7. After every slot is terminal, unblind once, build the all-slot pool, deterministic Current target, readiness and estimate artifacts, final closeout, independent verification, and the post-study isolation comparison while the locked source remains unchanged.
8. Close the run-lock window, update deferred task checkboxes, then run focused and full pytest, strict OpenSpec validation, and Git byte checks.

Rollback before collection removes the explicit exploration config and study lock without changing normal gameplay. After collection begins, rollback means stopping the study and writing a blocked closeout; collected source evidence is retained and never silently reclassified.

## Open Questions

None. The sample budget, behavior rates, alternatives, integrity policy, evidence thresholds, and authority boundary are fixed by the approved design.
