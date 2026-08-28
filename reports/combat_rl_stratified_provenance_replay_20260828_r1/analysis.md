# Combat RL Stratified Provenance Replay R1

## Result

The registered ten-game collection completed all seeds in order and retained
2,091 real combat transitions. No optimizer update occurred: online and target
weights remain byte-equivalent to production r16, optimizer state is empty,
and `learning_starts=100000` remained above the replay count.

The replay passes the preregistered training-input gate. All 391 direct
unmarked actions equal the frozen production-r16 eval-mode greedy action. The
other 1,700 rows are legal executed-action overrides, leaving both provenance
strata nonempty for the fixed stratified objective.

## Evidence Binding

The retained `.2`, `.1`, and current debug logs cover all ten games. They
contain 928 RL proposals, no current-batch traceback, no RL action failure, and
one natural max-games exit. Replay provenance reconciles exactly:

- `1,700 = 1,163 no-proposal actions + 537 changed proposals`
- `391 = 928 proposals - 537 changed proposals`

The clean decision trace has 2,091 joinable combat actions. Every row matches
replay floor and action family. Inventory identity joins one-to-one with zero
potion or relic mismatch and zero unresolved occupied object. There are no
cross-floor nonterminal successors.

## Training Decision

Approve checkpoint
`606727df27dd82ac825767097b71f07d6aa39ad37e0ea5d5d432e88c9288c28f`
only for the preregistered 64-update stratified successor. This is not
policy-quality evidence: the ten runs had no victory, and these seeds cannot be
reused for candidate selection, fresh confirmation, or promotion.

The next step is to implement the fixed runner and gates, verify that code once
at the capability boundary, then execute exactly one CPU fit without a
same-corpus sweep.
