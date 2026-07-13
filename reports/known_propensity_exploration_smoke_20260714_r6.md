# Known-Propensity Exploration Post-Fix Smoke R6 - 2026-07-14

## Scope

- Source commit: `830e376a1893cdd487f1b0e0e0af39ccdb766b70`
- Python: `D:\anaconda\envs\stsai\python.exe`
- Agent: `combat_rl`, conservative route, Ascension 0, evaluation mode
- Exploration rates: `card_reward=1000/10000`, `shop=1000/10000`
- Per-run alternative budget: `2`
- Training: disabled
- Session: `known-propensity-smoke-20260714-r6`

The persisted CommunicationMod command still specified `--max-games 25`.
This smoke was operationally bounded instead: it stopped immediately after the
first completed run because that trajectory exercised both repaired alternative
paths. A second trajectory had started before shutdown and is retained only as
unmatched diagnostic evidence.

## Live Result

- Completed run: `1783972051.run`
- AI marker: `1783972055`
- Floor reached: `16`
- Victory: `false`
- Killed by: `Hexaghost`
- Playtime: `64` seconds
- CommunicationMod suspicious rows after the R6 marker: `0`
- Remaining Slay the Spire, ModTheSpire, or AI processes after shutdown: `0`

The AI log contains two adjacent startup errors for a stale `start` command at
`03:46:26`. The agent was already on a live screen, recovered immediately, and
completed the run. No later strict ERROR, CRITICAL, or traceback row appears in
the frozen R6 log. This repeats the bounded B1 startup limitation and is not an
exploration confirmation failure.

## Transaction-Fix Evidence

The completed trajectory produced four confirmed decisions:

- Card reward baseline: floor 1, take `Twin Strike`.
- Shop alternative: floor 2, `shop:leave` instead of baseline `shop:purge`.
- Card reward baseline: floor 4, take `Perfected Strike`.
- Card reward alternative: floor 10, `card_reward:skip` instead of baseline
  take `Anger`.

The bounded final-action trace contains one `LeaveAction` in the shop decision
window and one `CancelAction` in the floor-10 card-reward decision window. It
contains neither the previewed purge action nor the previewed `Anger` take.
The completed run records no purchased or purged item, and its final deck does
not contain `Anger`. These live observations agree with the transaction
regressions that restore preview bookkeeping and commit only the selected arm.

This smoke validates action routing, confirmation, and externally visible game
state. It does not establish policy quality, causal effect, or general outcome
improvement.

## Evidence Validation

- Proposed records: `8`
- Resolution records: `8`
- Confirmed known-propensity records: `8`
- Replay-valid records: `8`
- Candidate-legal records: `8`
- Verified behavior propensities: `8`
- Exclusions: `0`
- Outcome-matched samples: `4`
- Source provenance verified: `true`
- Post-session isolation verified: `true`

The completed trajectory contributes card-reward baseline `2`, card-reward
alternative `1`, and shop alternative `1`. The interrupted second trajectory
contributes four structurally valid records, but all four retain
`join_status=missing` and are excluded from outcome support.

## Qualification Boundary

Known-propensity exploration data ready remains `false`. This one-run smoke is
blocked by the unique-trajectory minimum and every per-category arm-support
minimum. OPE, causal uplift, formal non-combat RL training, and live policy
promotion remain explicitly `false`.

## Frozen Artifacts

- Config SHA-256: `304e57da3c1cdc77228a19df1e0728b6014d7ee50469ed1176640b905d47e9f2`
- Trace SHA-256: `420bb5c4798ed3118fc2679e0b8588e179cfe3c77c3337cbf82ba48028899462`
- Manifest file SHA-256: `f7ac9c03397bc5f465d6cbaa6203fc0ef1b205a89fde676347d16b415456a994`
- Manifest logical hash: `7908335d34cd3bed74a2291757bf27159269d574939f7ba52e21dbec537e1e65`
- Effective config hash: `d49c777c9b22fa0d3a71b81fbe6c583e3255f5e86ac1c1271c2a231515c95109`
- Pre-isolation SHA-256: `457068ab0c16b5598b8cd7407d319f18aff50c7a2cb88ca79715eb148d9bb5b9`
- Post-isolation SHA-256: `92c12d4e8077590e8c53bbbec55dbb80e56f3e3633761e9999e280bbe8a1429a`
- Run allowlist SHA-256: `966535e89ef23be1d0fc6a81738205d7edcec4d72d0606a690e5590f70f30497`
- Run SHA-256: `62d49e8783e67ded817314cfa209fe775dbfda482edd1a92daa32e94e8a87838`
- Samples SHA-256: `b7354f29205864d914f745a31b371b1e33678c0a4bfdf5e349e249be25945601`
- Export summary SHA-256: `375f23e841cf52c4aae36f38239d6916e6a34d65477f4fe1094fde58e5079023`
- Qualification JSON SHA-256: `4cef00da0be179bba8124183a82a3b450c770b43d850f288d160daee4cd50ac8`
- Qualification Markdown SHA-256: `4f6376e495b4f68af791fa7470f4aeed0783c867e96735a5beaaa2830cd0721d`
- Diagnostics SHA-256: `dae0fe571855c31ca90b3ca33d274c82e26a0d08feb693540a433d5dd6b9715c`
- AI debug gzip SHA-256: `c601a3d146437bd8d79cbfd56e6b877c7ea9b07203b3d8c581e6bd49b5d49bd5`
- AI debug payload SHA-256: `71a04a067fdfcc196637d6c5fa3bb5185eb269042fcbbfbd0b5376fe9140399d`
- CommunicationMod slice SHA-256: `fbdcbe9b54a04989fed23e0e6e6b4aeb2953d0477480149297b8659d020d912c`
- Selected-action trace gzip SHA-256: `eb12b700e72a920937bd17b7b8eb1eb558a81d93e0c697beea9fc1dd6e3a6161`
- Selected-action trace payload SHA-256: `c885cbcf021941ae73364791f7c0dc69b8bdf57ce8fac9d2bba2a1001a613b14`

The config, complete exploration trace, manifest, isolation snapshots, exact
run allowlist and copy, canonical samples, qualification outputs, diagnostics,
and bounded raw log/action slices are stored beside this report.
