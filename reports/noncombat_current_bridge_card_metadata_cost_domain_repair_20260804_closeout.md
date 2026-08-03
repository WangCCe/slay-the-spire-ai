# Current Bridge Card Metadata Cost-Domain Repair Closeout

Date: 2026-08-04

Status: `offline_card_metadata_cost_compatibility_repaired`

## Boundary

This repair is bound to the committed read-only audit at `6d448fcc5` and the
OpenSpec planning baseline at `914ed9bf34d99c1259e21cf793deaa07d2b2e584`.
It changes only offline `MetadataCatalog` hydration and its regressions. It did
not load native code, construct a simulator environment, access a seed, launch
gameplay, execute Current, fit a model, run OPE, change a reward, train, qualify,
promote, retry the terminal study, or reinterpret its partial rows.

## Repair

- Added one exact 20-entry stable-native-ID table for the audited empty-cost
  records whose descriptions begin with `Unplayable.`.
- Required exact source name, selected metadata name, metadata type, empty cost,
  and description prefix before hydrating SpireComm cost and cost-for-turn `-2`.
- Kept every listed identity on the closed validation path before generic
  integer, `X`, or literal-unplayable parsing.
- Preserved all unlisted empty-cost failures, including `BECOME_ALMIGHTY`,
  `FAME_AND_FORTUNE`, and `LIVE_FOREVER`.
- Preserved numeric `SLIMED` and `PRIDE`, `WHIRLWIND` `X -> -1`, upgrades,
  source slots, misc, price, rarity, typed identity, and source non-mutation.

Implementation source after repair:

- `analysis_scripts/noncombat_current_policy_simulator_bridge.py`
- size: `102473` bytes
- SHA-256: `35041bf1b3c219411d7b121d8a2e700e19604de61e45cfda1b44d1a48fa8f99f`

Regression source after repair:

- `tests/test_noncombat_current_policy_simulator_bridge.py`
- size: `65535` bytes
- SHA-256: `84d35f09107f9908df3b1a5f06e445abc742f969021c79686f297e273f7f4ebe`

## Verification

- Red selection before production changes: 30 failed, 7 passed, and 100
  deselected in 6.52s. All 20 exact identities, three upgraded Skills,
  production-shaped `INJURY`, and registered drift blockers failed for the
  expected old behavior.
- Final focused cost-domain selection: `39 passed, 100 deselected in 1.05s`.
- Adjacent offline bridge, diagnostic, study-verifier, and adapter selection:
  `263 passed, 5 skipped in 31.23s`.
- Python compilation: passed for the implementation and regression files.
- Pre-archive strict OpenSpec validation: `63 passed, 0 failed` across the
  complete tree.
- Post-archive strict OpenSpec validation: `62 passed, 0 failed` across the
  complete active tree.
- Registered commit gate, executed once: `3703 passed, 11 skipped in 251.30s`;
  gate elapsed time `254.41s`.
- No raw full-suite retry and no gameplay validation were run.

The completed change is archived at
`openspec/changes/archive/2026-08-03-fix-current-bridge-card-metadata-cost-domain`.

## Evidence Preservation

The audit JSON and Markdown remain the repair authority:

- JSON SHA-256:
  `bd8c18241a012da3bbd786e09067edb503cdb3f9aa9003df1fb4a199a79a2230`
- Markdown SHA-256:
  `73a314284683171c63edfb4c7696ddf84376fa51cfcb15deeeb6e7e01bb2c4b3`

A raw working-blob comparison against `HEAD` covered every tracked
`noncombat_current_baseline_evidence_study_*` and
`noncombat_current_baseline_readiness_refresh_*` path. All `17/17` files were
unchanged, with no mismatch. The terminal registration, execution
authorization, preflight, preimplementation record, journal, retained rows,
bootstrap placeholder, metrics, report, manifest, blocked verdict, closeout,
and readiness refresh therefore remain byte-for-byte intact.

## Verdict

The known empty-cost unplayable metadata representation defect is repaired for
future offline Current bridge use. This is implementation compatibility only.
It does not complete the consumed canary, establish a Current baseline floor,
add a target-supported victory, or change the formal non-combat RL verdict.
Baseline policy and outcome support remain blocked, so formal RL remains
`not_ready_for_bounded_training_proposal` and `no_go`.
