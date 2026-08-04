## Why

The all-false r2 preregistration is pushed and independently verified, and the
user has now explicitly authorized one bounded execution with its exact cohort,
resource, output, isolation, and no-retry boundaries. This change records that
authorization and carries the single simulator-only run through fail-closed
preflight, execution, independent verification, and terminal publication.

## What Changes

- Create and push one canonical execution authorization for registration
  `8e0576bbf86b2334ccce67ac809410a02dcbfa6419f075211bbe48d0164f8549`,
  logical identity `noncombat-simulator-rl-20260804-r2`, and output
  `reports/noncombat_simulator_rl_experiment_20260804_r2`.
- Run source-only preflight against the pushed controls, repaired source,
  registered native module, physical simulator, Windows runtime, absent output,
  free lease, and unchanged production checkpoint inventory.
- Only after preflight passes, execute or resume that one logical attempt on CPU
  for at most `28,800` cumulative seconds and at most `5,504` total train,
  replay, canary, and conditional holdout episodes over `50000..51663`.
- Publish and independently verify the exact reached terminal state. A valid
  negative, canary stop, learning-signal result, or fail-closed block all count
  as completed experimental outcomes; no result authorizes live loading or
  promotion.
- Do not launch Slay the Spire or contact CommunicationMod, load or mutate
  production checkpoints, change any source/module/path/cohort/parameter, retry
  after the started journal, or reinterpret r1.
- Success is one independently verified canonical terminal artifact set under
  the registered bounds. Before the started journal, a failed validation stops
  with no output and no automatic retry; after start, the exact terminal state
  is immutable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-simulator-rl-experiment`: Bind and execute the explicitly approved
  r2 logical attempt under the existing successor, pre-start, one-shot,
  isolation, resource, evaluation, and publication requirements.

## Impact

The change writes one authorization, one preflight report, and the registered
terminal experiment artifacts under `reports/`, plus OpenSpec and project
direction closeout. It uses the existing Windows Python, native adapter, and
`D:\CLionProjects\sts_lightspeed` checkout. It does not modify Python source,
native/simulator source, gameplay policy, CommunicationMod configuration, game
processes, or production checkpoints.
