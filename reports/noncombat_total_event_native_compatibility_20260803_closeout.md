# API v3 Total Event Native Compatibility Closeout

Date: 2026-08-03

## Result

The one-shot API v3 native compatibility cohort is complete and preserved with
the structural verdict `total_event_native_compatibility_failed`. It is not
eligible for retry, alternate seeds, threshold changes, or reinterpretation as
policy-quality evidence.

The first execution blocker was:

- reason: `event_option_semantics_event_unsupported`;
- detail: `Scrap Ooze`;
- completed deterministic seed rows: `0`;
- observed card-reward, event, route, and shop decisions: `0` each; and
- execution journal: finalized, whole cohort consumed, noncanonical failure.

The simulator source confirms that `Scrap Ooze` is reachable in the Act 1 event
pool and exposes two choices whose first-choice HP loss and relic chance depend
on `eventData`. The frozen 25-event observation contract contains no Scrap Ooze
rule. This is therefore a missing reachable event surface, not an alias-only
identity mismatch.

## Frozen Evidence

- Preregistration commit:
  `61b74cb9332c4889ec25764dd72de5e934eb9e3e`
- Registration SHA-256:
  `5db0c2f6676a332126260207c9da082a50eb5fc304c116e226183a1252879b11`
- Seed-ledger SHA-256:
  `1a5fe44695ecb3bbbb2db8dc41dc9feb260a8074d47a2588e8cd94d1a154a136`
- Native module SHA-256:
  `410ac6b742192cfcd3568e36975bc87ecab4c2de9093d30113258b74a887e8cb`
- Simulator source SHA-256:
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`
- Total observation contract SHA-256:
  `785e5db26d4cecaa843c7ee3e9e276fdc98c4b77b6a61e88f4520824a50bf3fc`
- Registered cohort: seeds `7000..7007`, two replays per seed, at most
  500 decisions per replay and 120 wall-clock seconds total.

Before execution, tracked-clean status, exact registration bytes at `HEAD`, and
`HEAD == origin/master` were proved. The output directory did not exist. The
runner then atomically wrote the whole-cohort started journal before the first
environment and finalized the result without a retry. The no-native verifier
recomputed the preserved configuration, failed execution payload, metrics,
report, journal binding, and manifest successfully.

## Verification

- No-native artifact verification: passed with preserved verdict
  `total_event_native_compatibility_failed`.
- Focused compatibility, bridge, observation-contract, and resolver tests:
  `110 passed in 3.73s`.
- Repository commit gate: `3439 passed, 11 skipped in 269.07s`; gate total
  `272.46s`.
- Strict global OpenSpec validation before spec sync: `58 passed, 0 failed`.
- Strict global OpenSpec validation after sync: `59 passed, 0 failed`.
- Strict global OpenSpec validation after archive: `58 passed, 0 failed`.

## Authority Boundary

All gameplay, baseline-floor, target-supported outcome, reward, model, OPE,
formal-RL, training, qualification, loading, and promotion authority remains
false. No baseline-floor proposal is allowed from this result.

No live gameplay, Communication Mod process, model fitting, reward change,
training, qualification, policy loading, or promotion ran. The only native
execution was the exact preregistered compatibility cohort, and its seeds are
now consumed.

## Project Direction

The structural blocker remains active. The next change should not spend fresh
seeds on another compatibility cohort. It should first perform a read-only,
source-complete audit of every simulator-reachable event and phase against the
frozen observation contract and Current policy entrypoint, then define and test
the smallest additive contract and resolver extension that closes the complete
reachable surface. Only after that implementation is committed, reviewed, and
verified may a separately preregistered compatibility cohort use untouched
seeds.

Formal non-combat RL remains downstream of this compatibility gate, a credible
non-teacher baseline floor, and the independent target-supported-outcome gate.
