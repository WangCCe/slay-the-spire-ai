# Cross-Fitted Execution Bottleneck Audit

## Decision

Do not resume or rerun the consumed identity. Do not start a full
policy-quality experiment or formal non-combat RL training. The next change
should be a new source-only OpenSpec proposal for execution control-plane
throughput, elapsed-time accounting, terminal publication, and true-child
lifecycle supervision.

This audit loads no native module, imports no Torch, accesses no seed, and
modifies no terminal artifact. It explains why the authorized mechanism run
produced no complete chunk before its fixed wall-time gate.

## Finding 1: Registration Validation Dominates Access Control

The consumed output embeds a 63,171,200-byte registration with 275,853 source
provenance rows. Parsing that JSON once took 0.530 seconds. One source-only call
to `_registration_for_identity` took 56.016 seconds, without importing Torch or
the native adapter.

That helper first calls `validate_registration`, then calls
`registration_sha256`, which validates the complete registration again. The
per-access call graph compounds this work:

- `append_access_debit` validates output/identity, loads and replays the
  journal, then validates the candidate journal again;
- `reconcile_resource_ledger_from_journal` validates output/identity, reloads
  the journal, advances the ledger, and reloads the journal inside that
  advance; and
- `append_access_terminal` repeats output/identity, journal-load, and candidate
  journal validation.

Counting only `_registration_for_identity` entries gives a lower bound of 14
calls for `begin_environment_access` and 6 for a completed terminal record: 20
helper calls, or at least 40 complete registration validations per completed
access. Journal header reconstruction performs additional registration hashing
outside that lower bound. At the measured helper cost, those 20 calls alone are
about 1,120 seconds per completed access.

The observed result is consistent: the run completed only 11 accesses before
the four-hour runtime deadline, then durably debited seed `1780` and failed its
pre-construction deadline check. Existing evidence cannot separately estimate
native episode time until this control-plane amplification is removed.

## Finding 2: Failed Elapsed Time Is Missing From The Ledger

The terminal bundle is internally valid but reports `charged_seconds=0.0`.
Source inspection shows elapsed time is persisted when a complete checkpoint is
published and when an exception is classified as infrastructure interruption.
The non-infrastructure exception branch writes its failure witness and closes
the terminal bundle without charging elapsed time.

This run failed before its first checkpoint with `RuntimeBlocked`, so all 12
access debits remained visible while the elapsed resource stayed at its zero
origin. A future control plane must advance elapsed charge on every terminal
path before publishing intent, and the independent verifier must reject a
post-start terminal whose time coordinate is inconsistent with its failure.

## Finding 3: Terminal Publication Repeats The Same Work

Producer closeout took about 2,228 seconds from failure witness to manifest by
noncanonical filesystem timestamps. `publish_terminal_intent`,
`load_terminal_intent`, `_expected_terminal_document`, and
`publish_terminal_bundle` repeatedly normalize and hash the registration,
replay journals and checkpoint state, and rebuild managed inventories. The
independent standard-library verifier later accepted the closed bundle in about
15 seconds, showing that the terminal artifact itself is not intrinsically a
multi-minute verification problem.

The repair should build intent, terminal, and manifest from one immutable
validated execution context and one managed-artifact snapshot. Independent
post-exit verification must remain complete and separate.

## Finding 4: Wrapper Exit Was Not Child Exit

The command wrapper returned `124` after five hours while the Python child
continued to hold the output lease and finish terminal publication. Treating
the wrapper result as process exit caused one read-only active-root inspection;
the first verifier attempt correctly blocked on the live lease. No artifact was
mutated, and monitoring returned to liveness only until the original child
exited naturally.

Future supervision must track the actual Python child or an owning job object.
An outer timeout must not be interpreted as a closed output root, and it must
not be shorter than the registered execution plus bounded closeout without an
explicit interruption protocol.

## Required Repair Boundary

The next OpenSpec proposal should:

1. validate and digest registration once into a typed immutable execution
   context before native loading;
2. use that context through journals, resources, checkpoints, and closeout
   while preserving durable-byte and schedule checks;
3. add structural tests proving no registration-size work occurs per seed or
   nested terminal helper and proving corrupted boundary inputs still fail;
4. charge elapsed time on every terminal path, including first-chunk
   non-infrastructure failures;
5. publish terminal intent, terminal, and manifest from one validated snapshot
   and inventory; and
6. supervise true child liveness and keep active-root monitoring read-free.

All validation must remain source-only and synthetic until these regressions
pass. Any future mechanism execution needs a new identity, fresh registration
and cohort decision, and separate exact approval. This audit authorizes no
native loading, seed access, training, model loading, gameplay, evaluation,
formal RL, qualification, or promotion.
