# Promoted alpha-0.20 production validation r2

The promoted production command completed another bounded five-game launch without runtime failures. Floors were `29, 33, 31, 33, 16`, for a mean of `28.4`; four games entered Act 2 and two reached the Act 2 boss. No victory was achieved.

The new launch-time trace reset reduced the inherited decision trace from `2,407,726,683` bytes to a bounded `7,104,105` bytes after the batch, and reduced the simulator trace from `155,337,644` bytes to `15,113` bytes. The launch therefore removed approximately 2.56 GB of stale trace data while preserving current-batch evidence. Full traces are intentionally not copied into Git.

The current-batch simulator trace contained one deterministic `player_state_mismatch`: Reaper dealt 4 unblocked damage while Magic Flower was held, so the game healed 6 HP but the simulator predicted 4 HP. The accompanying source change applies Magic Flower scaling to Reaper healing in both the divergence predictor and the combat decision simulator, with focused regressions for the relic and no-relic cases.

This batch supports retaining the promoted checkpoint. Its main new evidence is that bounded trace capture works in production and exposed one narrow mechanics defect suitable for a direct fix.
