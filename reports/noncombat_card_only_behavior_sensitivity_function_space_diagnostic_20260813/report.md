# Card-only behavior sensitivity function-space diagnostic

## Result

- Probe rows: 175
- Exact action flips: 0
- Family flips: 0
- Global parameter L2 movement: 1.496854485
- Mean joint symmetric KL: 0.003256890
- Max joint symmetric KL: 0.065750730
- Mean joint total variation: 0.011298590
- Rows moving toward a greedy boundary: 92
- Final two-stage margin median: 4.672797680
- Parameter path/net ratio: 1.187248
- Negative consecutive update cosines: 0
- Mean Bottled target joint log-probability delta: 0.009527354
- Bottled target joint probability improved rows: 88/175

## Parameter movement

- Family head L2: 0.908563679 (0.045572 relative)
- Conditional ranker L2: 1.189573617 (0.096175 relative)

## Evidence coverage

- Entry and final model bytes, fixed probe rows, probabilities, entropies, and greedy margins are available.
- Per-step advantages, component gradients, and clipping evidence were produced in memory but were not persisted by the r1 runner.
- This diagnostic therefore identifies where the policy function moved; it cannot retrospectively attribute that movement to advantage scaling or clipping.

## Decision boundary

- No checkpoint is selected and no training, native environment, fresh evaluation, gameplay, or production loading is authorized.
- Use the measured distribution and margin movement to choose one separately registered training change.
