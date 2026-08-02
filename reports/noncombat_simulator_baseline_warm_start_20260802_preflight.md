# Non-Combat Simulator Baseline Warm-Start Preflight

Recorded at `2026-08-02T16:57:09.7047676+08:00`, before any registered
train, validation, or final-test seed was accessed.

## Frozen identity

- Reviewed and pushed HEAD: `6355e93b7da52d7ac3df686d15834293f396fc6d`.
- Registration SHA-256:
  `2815274e61c7d4ad8e553190ca234d6303457d9543cd63def541637729340a7a`.
- Registration hash closure: `10` bound repository artifacts, all matched.
- Runtime identity mismatches: none.
- Registered native module SHA-256:
  `b3328aea4ee3040a4fe8751d6f300a148a7ae64d68f7ebec050ae61f479d6805`.
- Registered native module size: `1550848` bytes.
- The tracked worktree and index were clean. Known unrelated untracked reports
  and `.adaptive_route_poc/` were excluded from every command and commit.

## Pre-execution gates

- The registered optional module had already been rebuilt in this gate with
  the fixed CLion/Ninja toolchain; Ninja reported `no work to do`, and the
  rebuilt bytes matched the registered module identity above.
- The exact compatibility plus focused opt-in native gate passed `4` tests in
  `22.89` seconds.
- The focused warm-start pure gate passed `34` tests with `3` explicit native
  skips in `37.71` seconds.
- The registered repository commit gate passed `3239` tests with `11` skips in
  `223.41` seconds (`226.58` seconds including runner overhead). It used a
  unique writable basetemp and excluded only the two registered full-only
  outcome-evidence files; the unbounded raw full suite was not used.
- Python compilation passed for the implementation and both warm-start test
  modules.
- `openspec validate add-noncombat-baseline-warm-start --strict` passed.
- A resumed build refresh reached CMake's glob recheck but was terminated at
  its bounded timeout. It produced no changed module bytes and left no CMake,
  Ninja, or compiler process. This refresh is not counted as gate evidence;
  the completed rebuild, exact module hash, successful native tests, module
  import, and zero-mismatch physical identity check are the gate evidence.

## Isolation baseline

- Slay the Spire / Java process count: `0`.
- Relevant Python gameplay, batch, training, or warm-start study process
  count: `0`.
- CommunicationMod configuration SHA-256:
  `7ec79e01f9293a19ead3c59a26b18bb75ef900afa3dbe45d657769fe46061862`.
- CommunicationMod configuration size: `534` bytes.
- CommunicationMod configuration last write:
  `2026-08-02T05:54:54.3279792+08:00`.
- The configuration still names the bounded live evaluation batch, but this
  study does not invoke CommunicationMod and the configuration was not changed.
- Checkpoint file count: `208`.
- Checkpoint inventory SHA-256, over sorted
  `name|size|last-write-UTC-ticks` rows:
  `2310129f2d0589b088ef27dd30d17f11d03af03bfd190b15f7e16bd1513ad1ef`.
- Latest checkpoint last write: `2026-06-04T02:44:50.0352542+08:00`.
- Target study output directory did not exist.

## Execution authorization

The only authorized next command is the checked-in `study` CLI using train
seeds `4000..4031`, validation seeds `5000..5015`, and final-test seeds
`6000..6031`. It may run exactly one primary execution and one identical
replay. Final-test access remains conditional on the preregistered validation
gate. No tuning, seed substitution, retry after observation, live gameplay,
formal RL training, qualification, promotion, or deployment authority is
granted.
