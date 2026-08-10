## Why

The sole r2 inventory process failed before authority validation because its
registered `python -I <script-path>` entrypoint could not import the configured
`analysis_scripts` control module. A successor identity must not be published
until that exact isolated dispatch path is executable and regression-tested
without consuming empirical evidence or a one-shot receipt.

## What Changes

- Add a source-only `check-dispatch` command to the existing seed-inventory CLI
  that imports and identifies the configured control module, then exits before
  authority files, Git evidence, candidate blobs, seeds, receipt paths, or
  output paths are accessed.
- Make direct isolated script execution resolve only the script's fixed
  repository root before importing the configured control module, while
  preserving Python isolated mode and the existing import boundary.
- Add a subprocess regression using the production Windows interpreter shape,
  exact working directory, `-I`, and script path; assert canonical output,
  deterministic repetition, and absence of empirical side effects.
- Bind any later r3 proposal to the tested source commit and exact dispatch
  command. This change itself creates no r3 request or execution authority.
- Live evidence is r2 failure
  `d44f6d900c902d94af20fba365725e9cc46c423a3ab10cbcedf16747e80ec3fb`
  at the pre-start control-module import boundary. Success is the focused
  subprocess regression plus the complete seed-inventory test file, strict
  OpenSpec validation, and independent review with no unresolved finding.
- Non-goals are inventory construction or verification, seed discovery,
  registration, native/model/environment loading, training, evaluation,
  gameplay, CommunicationMod, qualification, and promotion.
- Rollback removes the probe and bootstrap before any successor authority is
  published; r1 and r2 terminal evidence remains immutable in all cases.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Require a side-effect-free
  exact isolated-dispatch check before a future inventory successor may publish
  authority.

## Impact

The change affects only
`analysis_scripts/noncombat_card_acceptance_empirical_successor_seed_inventory.py`,
focused subprocess tests, OpenSpec records, and an optional source-only dispatch
observation. It does not change cohort selection, thresholds, algorithms,
runtime dependencies, production policy, checkpoints, CommunicationMod
configuration, or game behavior.
