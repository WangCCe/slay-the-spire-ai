# Guarded control matched live gate

## Decision

Retain production r16. The packaged LightSTS guarded-control candidate did not
pass its registered 10-pair live gate, so it is not eligible for promotion and
this cohort will not be extended.

## Outcome

Both arms completed all ten fresh seeds in the same order with no crash or RL
action failure. The candidate reached 211 total floors versus 216 for r16. It
won one floor pair, lost two, and tied seven; the paired floor delta was `-5`.
Neither arm won a run.

The candidate reached the Act 2 boss once while r16 did not, but r16 entered
Act 2 on six runs versus five. The only non-tied floor deltas were `-12`, `-5`,
and `+12`. That sparse result does not reproduce the large simulator advantage
seen in the two LightSTS cohorts.

## Qualification

Completion, seed identity, runtime health, victories, Act 2 boss reaches, and
Act 3 entries all met their registered conditions. The candidate failed the
required total-floor improvement (`211 <= 216`), making the full conjunction
false. The production r16 CommunicationMod configuration was restored exactly;
no automatic checkpoint change occurred.

## Interpretation

Seven exact floor ties show that most of this small cohort was behaviorally
unchanged at run-outcome granularity. The next useful work is a trace-level
comparison of the three divergent seeds, especially the first policy action
where candidate and parent separate. Another live gate is not justified until
that analysis produces a materially different simulator candidate or a clear
transfer correction.

The sim-divergence traces contain ten candidate rows and eight parent rows.
They are retained as mechanics-audit evidence, but are not counted as policy
runtime failures in this gate.
