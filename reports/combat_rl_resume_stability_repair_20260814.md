# Combat RL Resume Stability Repair - 2026-08-14

## Decision

The repaired ten-game combat RL candidate failed its preregistered zero-epsilon
matched gate and is not eligible for continued training. Before another update
batch, resume behavior must preserve enough training state to avoid immediately
reusing a newly empty replay buffer.

## Gate evidence

- Candidate floors: `[16, 20, 16, 16, 33, 22, 16, 16, 16, 16]`
- Frozen-entry floors: `[16, 50, 16, 16, 33, 21, 16, 16, 33, 16]`
- Candidate versus baseline: 1 paired win, 2 paired losses, 7 ties
- Both arms: zero victories and zero recorded integrity or NaN warnings
- Result: `FAIL`

The failed candidate performed 515 Adam updates from 2,187 accepted transitions.
At batch size 128, that is 65,920 replay samples drawn after resuming with an
empty buffer. The legacy checkpoint restored online weights, optimizer state,
epsilon, and counters, but did not contain replay or the lagged target network.
This is the strongest identified mechanism for unstable continuation; it is not
a causal claim that excludes reward scale, dropout, or exploration effects.

## Repair

- Schema-2 training checkpoints now include the lagged target network, a
  validated chronological replay tail capped at 4,096 transitions, optimizer
  state, counters, epsilon, episode count, and the learning-start threshold.
- Legacy and weights-only checkpoints still honor the existing optimizer restore
  contract. They clone online weights into the target network, clear replay, and
  enter a 4,096-transition collection warm-up before updates can resume.
- The warm-up threshold is persisted so a process restart cannot silently reduce
  it to the normal fresh-training threshold.
- Episode count advances only when a completed episode is finalized, not during
  reset, so checkpoint filenames and payload episode counts remain aligned.
- V2 checkpoint writes use a same-directory temporary file and atomic replace.
- Unknown future schemas, incomplete schema-2 training state, incompatible replay
  metadata, tensor shapes, dtypes, or actions are rejected.

This is a bounded warm start, not bit-exact continuation. It intentionally omits
older replay beyond 4,096 transitions and does not persist Python, NumPy, or
PyTorch RNG state.

## Practicality

A production-shape 4,096-transition replay prototype measured 15,500,248 bytes
for replay state, with approximately 0.06 seconds to build, 0.02 seconds to save,
0.03 seconds to load, and 0.05 seconds to restore on this machine. This keeps the
five-checkpoint retention policy practical without serializing the full 100,000
transition capacity.

## Verification

- Direct checkpoint/replay regressions: `21 passed in 7.49s`
- Final bounded caller gate: `114 passed in 11.95s`
- `git diff --check`: passed (line-ending conversion warnings only)
- Full pytest was intentionally not run; the changed behavior is covered by the
  RL v2 transition, action-space, context-guard, checkpoint I/O, batch-runner, and
  main-runtime test modules.

## Next live step

Start from the frozen legacy entry checkpoint and run a bounded replay-collection
batch. The online model and Adam step must remain unchanged while accepted
transitions and schema-2 replay state grow. Continue into an update batch only
after the persisted replay reaches the 4,096 learning-start threshold; evaluate
the resulting model with a fresh preregistered matched seed gate.
