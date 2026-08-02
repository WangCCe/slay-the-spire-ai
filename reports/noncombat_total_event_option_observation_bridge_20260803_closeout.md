# Non-Combat Total Event Option Observation Bridge Closeout

Date: 2026-08-03

## Result

The implementation-only total event observation bridge is complete. It is
ready for a separately preregistered native compatibility evaluation, but it
does not itself establish native compatibility or policy quality.

The implementation now:

- advances newly loaded native adapters to API v3 and exports exact N'loth
  offered-relic slot, id, name, and simulator-choice records;
- preserves explicit historical v2 snapshot and provenance readers without
  filling or upgrading their contents;
- reloads and hash-checks the canonical 25-event, 47-alias observation contract
  for every resolution, including all five Cursed Tome phases, N'loth dynamic
  context, and Current event-id normalization;
- carries contiguous Current positions separately from sparse simulator choice
  indices through enrichment, hydration, and reverse candidate mapping; and
- accepts legacy inline semantics only when both coordinate systems are exactly
  the same contiguous `0..n-1` sequence.

The frozen simulator-policy-validity registration remains byte-for-byte
unchanged. Its closure regression now verifies implementation source bytes at
the registration's bound commit instead of incorrectly comparing a historical
identity with the evolving working tree.

## Frozen Implementation

- OpenSpec proposal commit:
  `571f5f27ce330be366f1f6741132666ab2369e56`
- Implementation commit:
  `3c61e2d7ab230118035148a4efa216d82aad0ec6`
- OpenSpec archive:
  `openspec/changes/archive/2026-08-02-implement-total-event-option-observation-bridge/`
- Canonical observation contract:
  `reports/noncombat_event_option_observation_contract_20260802/contract.json`
- Canonical contract SHA-256:
  `785e5db26d4cecaa843c7ee3e9e276fdc98c4b77b6a61e88f4520824a50bf3fc`
- Resolver identity:
  `sts_lightspeed_total_event_observation_v2`
- New native adapter API:
  `sts-lightspeed-noncombat-adapter-v3`

## Verification

- Focused adapter/resolver/contract/bridge plus historical-closure regression:
  `96 passed, 5 skipped in 8.26s`.
- Python compile checks: passed.
- Strict change validation: passed.
- Global OpenSpec validation before closeout: `58 passed, 0 failed`.
- Global OpenSpec validation after archive: `57 passed, 0 failed`.
- Final repository commit gate: `3414 passed, 11 skipped in 264.80s`;
  gate total `267.91s`.

One sandboxed gate attempt created ACL-invalid pytest temporary directories and
timed out with setup errors. It is not verification evidence. The first
host-permission gate then exposed one historical-working-tree hash assertion;
the commit-bound regression above fixed that test contract. The final
host-permission gate is the authoritative result.

No native module was built or loaded. No simulator environment, seed, cohort,
gameplay process, model, reward, baseline study, trainer, or policy promotion
ran in this change.

## Authority Boundary

The following remain false:

- native compatibility;
- baseline-floor readiness;
- target-supported outcome readiness;
- reward selection or reinterpretation;
- formal non-combat RL readiness or training;
- live gameplay loading or evaluation; and
- policy qualification or promotion.

## Next Boundary

The next change must preregister a v3 native compatibility evaluation before
constructing an environment or reading a seed. It must bind the built module,
adapter and simulator sources, total observation contract, resolver, bridge,
metadata, runtime, candidate cohort, deterministic replay, stop rules, and
structural-only authority. Consumed seeds `2000..2003` must not be reused.

Passing that compatibility gate would permit consideration of a separate
non-teacher baseline-floor study. It would not authorize formal RL training or
resolve the independent target-supported-outcome blocker.
