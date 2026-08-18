# Promoted-r16 successor r19 matched live gate

## Decision

Close the registered cohort without qualification. The candidate arm was
externally interrupted during game 16 after 15 completed games; the parent arm
was not started. Retain production r16. This is not a rejection or promotion of
r19, and the same cohort must not be resumed or rerun.

## Evidence

Candidate floors for the 15 completed seed-prefix games were
`[16, 16, 16, 33, 18, 28, 16, 16, 16, 16, 50, 16, 16, 16, 16]`.
They total 305 floors, with four Act 2 entries, two Act 2 boss reaches, one Act
3 entry, and no victory. The completed run seeds match the first 15 registered
seeds in order.

During game 16, the last stable state was a floor-5 map screen. The log then
recorded `STDIN PIPE BROKEN`, an EOFError, and `Game #16 CRASHED`. The user
reported interacting with Steam and possibly closing the game at that time.
There was no RL action failure before the shutdown. Because the interruption
occurred after completed games, the preregistration forbids native recovery.

## Scope

No paired result or qualification condition can be evaluated without the parent
arm. R19 remains frozen and live-unqualified; r16 remains production. Before
deciding whether a separately registered new r19 gate is worth running, revisit
LightSTS and offline replay candidate generation so real-game cost is reserved
for candidates with greater expected information gain.
