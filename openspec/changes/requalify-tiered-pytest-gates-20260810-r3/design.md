## Context

The five-minute `commit` qualification at `52edf92f8` covered 3,571 passing
tests and 16 skips in 262.89 gate seconds with 17 `full_only` files. The runner,
manifest, and pytest configuration are unchanged, but seven new ordinary
card-acceptance test files were added afterward. A frozen successor-source gate
passed in 515.35 seconds; the current gate passed 3,918 tests and 16 skips in
528.59 seconds. Correctness is green and feedback latency is unqualified.

The seven files total 9,959 lines at the pre-dispatch audit boundary and own
specialized source-only authority, subprocess, runtime, verifier, inventory,
objective, and policy behavior. The existing conditional-choice audit file is
already the seventeenth `full_only` entry and is not part of this candidate set.

## Goals / Non-Goals

**Goals:**

- Restore one measured `commit` result at or below 300 seconds.
- Keep all tests in unchanged `full` and preserve inclusive collection for
  every other ordinary test.
- Measure and document the exact seven-file attribution set before changing the
  manifest.
- Require direct affected-file or stricter focused coverage for source owned by
  the selected new full-only files.
- Preserve every final slow or failed result without retry or adaptive tuning.

**Non-Goals:**

- Changing test assertions, runtime behavior, the runner, pytest configuration,
  dependencies, parallelism, or the five-minute ceiling.
- Selecting extra candidates after attribution or final qualification.
- Changing simulator/RL/gameplay behavior or running inventory, training,
  evaluation, gameplay, CommunicationMod, or policy promotion.

## Decisions

### Freeze the complete post-qualification ordinary domain delta

The candidate set is exactly these seven files:

1. `tests/test_audit_card_acceptance_objective_interventions.py`
2. `tests/test_noncombat_card_acceptance_empirical_successor_control.py`
3. `tests/test_noncombat_card_acceptance_empirical_successor_runtime.py`
4. `tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py`
5. `tests/test_noncombat_card_acceptance_empirical_successor_verifier.py`
6. `tests/test_noncombat_card_acceptance_objective.py`
7. `tests/test_noncombat_card_acceptance_policy.py`

Git comparison from `52edf92f8` supplies the identity. The conditional-choice
file is excluded because it already has a measured `full_only` entry. No older
test, hierarchical full-only test, or future file is eligible.

The candidate universe stays fixed, but a file becomes full-only only when its
JUnit testcase times aggregate to at least 5.00 seconds. This threshold is fixed
before measurement, is below the smallest 7.39-second whole-file candidate used
in the prior requalification, and prevents cheap files from being excluded only
because they share a domain. The selected files must aggregate to at least
265.70 seconds, the exact current 528.59-second gate regression over the prior
262.89-second qualified result. If either condition cannot be established, the
change closes unqualified without a manifest edit.

### Measure attribution once before manifest publication

Use the production interpreter and one new system-temp pytest child to run the
seven files together with `-q -p no:cacheprovider --durations=50`,
`-o junit_family=xunit1`, `-o junit_duration_report=total`, and one JUnit XML
output. The explicit xUnit1 `testcase.file` attribute, normalized to forward-
slash repository-relative form, MUST uniquely name one of the seven frozen
files; aggregate every finite nonnegative testcase `time` by that attribute.
Preserve the complete terminal result, XML SHA-256, XML, and slow-node table.

The evidence is trustworthy only when pytest exits zero; the XML suite totals
equal the number of testcase elements and the terminal passed/skipped totals;
failures and errors are zero; every testcase maps uniquely to the frozen set;
every frozen file has at least one testcase; and the absolute difference
between the sum of all XML testcase times and pytest's terminal wall duration
is at most 30.00 seconds. These fixed checks fail closed before selection.
Apply only the preregistered 5.00/265.70-second rule after all checks pass. Do
not edit tests or tune thresholds in response. Each selected manifest rationale
cites its measured aggregate and domain responsibility.

Running files separately was rejected because repeated startup and shared
fixture costs would not represent their current combined commit contribution.

### Preserve direct ownership and unchanged full coverage

Update exact manifest membership from 17 to `17 + selected_count` files and
document only the selected ownership boundaries. A change to any owned source
runs every affected owner or a documented stricter set before `commit`; `full`
remains the phase-close boundary and contains every test.

### Qualify only after the boundary is frozen

After manifest, exact-membership tests, docs, report, strict OpenSpec, and
independent review are complete, record the base HEAD, a canonical diff hash,
and individual hashes for the gate-affecting manifest, runner test, and testing
documentation without committing or pushing the selection change. Record the
pre-gate report hash separately because only its open result fields may change
afterward. Preflight the registered temp root and required sandbox permission,
then verify the gate-affecting hashes immediately before and after each gate and
again before the selection commit. Run one final `commit`; require exit zero and
at most 300 seconds. Only a passing in-budget commit permits one unchanged
`full` because suite selection changed. An outer wait of 720 seconds for
`commit` and 3,600 seconds for `full` only observes the registered commands and
does not change pytest behavior.

An attribution failure or untrustworthy aggregate writes and independently
reviews a terminal report, skips manifest edits and final gates, then archives.
A failed or slow final `commit` writes a terminal report, restores only the
uncommitted manifest, runner-test, and docs selection draft, preserves the
report and OpenSpec evidence, skips `full`, and archives. A failed `full`
follows the same restoration and terminal closeout. No retry, candidate
addition, threshold change, or result reinterpretation follows any terminal
path.

## Risks / Trade-offs

- [Risk] Routine commit coverage loses the selected domain files. -> Mitigation:
  direct ownership is mandatory for relevant changes and unchanged `full`
  remains complete.
- [Risk] The selected exclusions still do not restore five minutes. -> Mitigation:
  preserve the result and leave timing unqualified; do not tune further.
- [Risk] Full takes about forty minutes. -> Mitigation: run it once only after
  focused evidence and final review are green.
- [Risk] Attribution itself fails. -> Mitigation: preserve the result and stop
  before manifest publication.

## Migration Plan

1. Commit and push this planning-only change to freeze the candidate set.
2. Run the exact seven-file attribution suite once, aggregate JUnit times, and
   apply the preregistered selection rule.
3. On an eligible result, update manifest membership/rationales, exact runner
   regressions, testing docs, and the dated report; run focused runner checks.
4. Freeze and independently review the complete uncommitted diff, then record
   the base HEAD, canonical diff hash, gate-affecting file hashes, and separate
   pre-gate report hash.
5. Preflight permission/temp state, verify the gate-affecting hashes, and run
   final `commit` once; only an in-budget pass permits unchanged `full` once.
   Verify hashes around both gates and restore the selection draft on either
   failure branch.
6. On success, finalize the report, reverify the gate-affecting hashes, commit
   and push the frozen selection, then sync/archive in an independent closeout
   commit and push. On failure, publish only the reviewed terminal report and
   archived planning evidence.

Rollback removes the selected manifest entries and associated tests/docs/report/
OpenSpec publication. It does not remove tests or change the full suite.

## Open Questions

None.
