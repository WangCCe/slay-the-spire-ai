# Combat RL expert target-normalization smoke R2

## Decision

**Pass. Start a fresh 25-game expert-dominant candidate from the unchanged entry checkpoint.** Across five games, 565 expert actions were selected, 257 were probability-skipped, and none were masked, failed, or unencodable. Successful expert use was `68.73%`, above the preregistered 68% floor.

The smoke stayed below `learning_starts=4096`, so it performed no optimizer updates and its checkpoint is diagnostic only. Five-game outcomes totaled 111 floors (mean `22.2`) with two Act 2 entries and one Act 2 boss reach.

No runtime-integrity failure occurred. CommunicationMod error-log growth was 556 bytes of expected launch messages; the original configuration and process state were restored.
