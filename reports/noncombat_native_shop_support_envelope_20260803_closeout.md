# Native Shop Support Envelope Closeout

Date: 2026-08-03

## Decision

The native adapter now fails closed for every shop decision where the player
already owns The Courier and omits impossible potion purchases when Sozu or a
full potion belt prevents obtaining the item. Supported shop inventory remains
visible in snapshots, and card, relic, removal, and leave candidates are not
changed.

This closeout does not authorize a third formal native cohort, gameplay,
training, reward use, OPE, loading, qualification, or promotion. It closes a
known-invalid simulator evidence surface and returns the project to a separate
non-combat RL training go/no-go assessment.

## Evidence Chain

- Source-complete remaining-shop audit: commit `fcbba6330` and
  `reports/noncombat_native_shop_domain_audit_20260803.md`.
- Pushed OpenSpec planning boundary: commit `3fa048651`.
- Minimal native support-envelope implementation: commit `cbacad62a`.
- Deterministic native blocker lifecycle regression: commit `b704c75ca`.

The source-contract regression first failed exactly because the shared Courier
guard and potion predicate were absent: `1 failed in 0.57s`. After the minimal
C++ change, the selected regression passed and the pure adapter file passed
`12 passed, 5 skipped in 0.34s`.

The first full native/bridge run passed 82 tests and failed only because the
old target-policy regression still required every reused development seed to
reach a terminal outcome. The new guard correctly stopped one trajectory. The
test was narrowed to preserve all prior determinism, candidate-legality, and
query-nonmutation assertions while locking the exact unsupported boundary.

## Implementation Boundary

At snapshot, candidate, and native-baseline entry points, a shop state with
The Courier throws exactly:

`unsupported_shop_courier_restock_semantics`

The adapter does not repair or approximate Courier replacement inventory,
price, RNG, card-type, discount, or purchased-relic preview behavior.

For a non-Courier shop, potion entries remain in `decision_context.potions`.
Only `buy_potion` candidates are omitted when the player owns Sozu or when
`potionCount >= potionCapacity`. The API remains
`sts-lightspeed-noncombat-adapter-v3`; no JSON field, Current policy, bridge,
purge observation, reward, model, or live-game code changed.

## Successor Provenance

The successor was built in the ignored directory
`.sts_lightspeed_adapter_v3_shop_support_build`. Neither frozen predecessor
directory was rebuilt or overwritten.

- Build-time adapter implementation commit:
  `cbacad62afcffd944aff856490458caa8e6d8328`
- Verification checkout after the test-only commit: `b704c75ca`
- Bound adapter source SHA-256:
  `571702a84e6d3e7da0d6d0fb3c6338257d3fad8e23f37884929792f7385d5f6f`
- `noncombat_adapter.cpp` SHA-256:
  `a2af70ccbf8f750478742a52e1a22ab1f90286938a9a8da81f5581c9a42d946d`
- Adapter `CMakeLists.txt` SHA-256:
  `709d4c081b3121f6497306085493ea78afc6fafb0887300d019ff8996d252220`
- Successor module SHA-256:
  `7ac2c750fba6e38d4a023cab72a4d67f158fe7f88414058e5876cef5003fcb88`
- Successor module size: `4225024` bytes
- Original frozen v3 module SHA-256 before and after:
  `410ac6b742192cfcd3568e36975bc87ecab4c2de9093d30113258b74a887e8cb`
- Sold-inventory successor SHA-256 before and after:
  `f5dde34657156db74e437bcb954fc0ceb739604bb43a3bcb10da5fd861bc48b8`
- Adapter API: `sts-lightspeed-noncombat-adapter-v3`
- Baseline policy: `sts_lightspeed_simple_agent_no_potions_v1`
- Native target policy: `sts_lightspeed_simple_agent_target_v1`
- Compiler: GCC `15.2.0`, C++ `201703`
- Python: `3.10.18`
- pybind11 build identity: `3.0.2a0`

The external simulator remained at commit
`7476a81954020087da31d41d16fddf475746ec2d` with compiled-source SHA-256
`a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`
over 79 files. Its pre-existing dirty state remained: modified root
`CMakeLists.txt`, checked-out `json` and `pybind11` submodules, and untracked
`AGENTS.md` and `CLAUDE.md`. The bound submodule commits were
`55f93686c01528224f448c19128836e7df245f72` for json and
`8f68ecd32c8e18d3b064dbf0ea5fc31a6cb37e9a` for pybind11.

The first provenance load attempt failed because Python 3.10 did not resolve
the MinGW runtime from `PATH` alone. Retrying through the adapter's explicit
`dll_directories` input loaded the same compiled bytes successfully; no source
or module rebuild occurred.

## Bounded Native Verification

No fresh formal seed was consumed. All native execution reused development
seeds `0..19` and the frozen historical-prefix fixtures.

- Reused-seed lifecycle plus historical fixtures:
  `3 passed in 6.97s`.
- Exact target-policy blocker regression:
  `1 passed in 121.80s`.
- Final native adapter plus Current bridge focused suite:
  `83 passed in 134.81s`.
- Partitioned repository commit gate:
  `3508 passed, 11 skipped in 236.88s`; total gate time `239.83s`.
- Strict OpenSpec validation: `60 passed, 0 failed`.

Across the logical seed set, exactly one target-policy trajectory stopped at
the support envelope: seed `10`, floor `21`, decision `39`, after route action
`route:map_node:6:4` reached a shop while owning The Courier. Both deterministic
replays produced the same action prefix and exact blocker. It is counted once,
not as a policy mismatch or terminal outcome.

No reused trajectory was selected to synthesize a Sozu or full-capacity shop
case. That predicate is covered by the red/green source contract, successful
native compilation, and supported-domain regressions; this closeout does not
claim direct runtime coverage for those two states.

## Immutable Evidence And Authority

Formal cohorts, their manifests and ledgers, prior native modules, game runs,
models, checkpoints, Communication Mod configuration, and external simulator
sources remained unchanged. No game, trainer, model loader, or Communication
Mod process was started.

- `baseline_floor_authorized = false`
- `fresh_evidence_authorized = false`
- `gameplay_authorized = false`
- `loading_authorized = false`
- `ope_authorized = false`
- `promotion_authorized = false`
- `qualification_authorized = false`
- `reward_authorized = false`
- `training_authorized = false`
- `formal_rl_readiness_authorized = false`

## Next Decision

Archive this support-envelope change, then perform a read-only refresh of the
non-combat RL training go/no-go evidence. The refresh must distinguish proven
adapter compatibility from reward, coverage, policy-validity, and evaluation
readiness. It must not launch training or manufacture a new cohort merely
because the native shop boundary is now narrower.
