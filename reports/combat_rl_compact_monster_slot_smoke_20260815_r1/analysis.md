# Combat RL compact monster-slot smoke R1

## Decision

**The compact live-monster slot repair passes its targeted live smoke. Proceed to one fresh bounded 25-game expert-dominant training batch from the frozen entry checkpoint.**

## Evidence

Both selected seeds entered Slime Boss. Across the two games, the v2 agent selected 398 expert actions with zero masked, failed, or unencodable expert actions. The live log contained five actions targeting raw monster index 6. Four came from the expert path; three were returned and executed directly, while one was subsequently replaced by the survival guard. This is the boundary that previously produced the remaining schema rejects.

The runs ended on floors 33 and 16. They are diagnostic outcomes, not policy-quality evidence: expert probability was intentionally fixed at 1.0 to maximize boundary coverage.

## Training state

The smoke accepted 424 transitions and produced a finite episode-17 continuation checkpoint. Replay grew from 1,565 to 1,989 transitions, below the learning threshold, so no optimizer update occurred and the checkpoint is not a promotion candidate.

## Operational note

The first launch attempt used signed `seed_played` integers copied from `.run` records. CommunicationMod rejected the negative value before any game or transition began. The successful attempt used the corresponding original seed strings recovered from the prior matched gate's ordered seed pool. The original CommunicationMod configuration was restored and all game/Python processes were closed.
