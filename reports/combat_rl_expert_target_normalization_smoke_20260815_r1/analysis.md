# Combat RL expert target-normalization smoke R1

## Decision

**The target-normalization repair is effective, but the zero-rejection smoke gate did not pass.** Successful expert use rose to `69.98%`, essentially the configured 70%, while six of 647 attempted expert actions were still rejected.

## Evidence

- Five games completed with 1,046 new transitions; the run stayed below `learning_starts=4096`, so no optimizer update occurred and this checkpoint is not a training candidate.
- Expert source: 641 selected, 269 probability skips, 6 masked, 0 failed, and 0 unencodable.
- The attempted expert share was `70.63%`; the masked share among attempts was `0.93%`.
- Five rejections were stale cached cards that were no longer playable after energy fell to 0 or 1.
- One rejection targeted raw `monster_index=6` after a summon/split sequence, beyond schema-2's five raw monster slots.

Commit `ac6a2ef5278b6c9a1b985ae30257b1e20c64b623` now makes OptimizedAgent replan when the next cached card is no longer playable. The raw monster-slot limit remains a separate schema issue and is not hidden by this repair.

## Outcomes and integrity

The five games totaled 129 floors (mean `25.8`) with four Act 2 entries and one Act 2 boss reach. There were no runtime-integrity failures. CommunicationMod error-log growth was 556 bytes of expected launch messages; configuration and process state were restored.

## Next step

Run a short post-cache-fix smoke. If stale-card rejections fall to zero and any remaining rejection is only the known raw monster-slot limit, run a fresh 25-game expert-dominant candidate from the unchanged entry checkpoint.
