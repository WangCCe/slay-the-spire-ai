# Replay distribution calibration r2 registration review

## Verdict

`ready_for_single_replacement_execution`

r2 is not a retry of r1. It binds the pushed deterministic `select_action`
compatibility repair and uses a fully fresh seed range while inheriting the
hashed r1 module, simulator, item, real replay, parent, comparison, and stop
contracts.

## Repair binding

- Repair commit: `d632f4d54482e0b4f68e1940f31408f455db631f`.
- Runner SHA-256:
  `8d8c12bc1308a2c0f18f5cfa9ebbe1f51c240e1c3fba28713cd13efac4482cf4`.
- Focused verification: `109 passed, 5 skipped`.
- The repair adds deterministic inference only; it constructs no optimizer and
  exposes no fitting method.

## Cohort and execution

The entire r1 range `180000..180127` remains reserved. The fresh r2 range
`181000..181127` has no tracked combat registration overlap and again covers
battle indices `0..12` for 1,664 profiles.

Execute r2 once on CPU with no game, CommunicationMod, optimizer update, retry,
resume, seed replacement, or threshold tuning. Any failure closes r2.
