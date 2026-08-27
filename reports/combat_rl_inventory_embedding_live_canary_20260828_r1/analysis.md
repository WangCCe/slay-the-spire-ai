# Inventory Embedding Matched Live Canary R1

## Decision

Retain production r16 and stop the inventory-only candidate line. The candidate
did not pass its registered 10-pair live canary, so the cohort is not extended
and the checkpoint is not promoted.

## Outcome

Both arms completed the same ten fresh seeds in order with no crash, traceback,
or RL action failure. Candidate and parent each reached 234 total floors, with
identical per-seed floors, death causes, Act 2 entries, Act 2 boss reaches, and
Act 3 entries. Neither arm won a run.

The frozen candidate was active: five seeds have different ordered raw RL action
logs, with 732 candidate actions versus 733 parent actions overall. Those
differences produced no run-outcome separation in this canary.

## Qualification

Completion, seed identity, runtime health, victories, Act 2 boss reaches, and
Act 3 entries met their registered conditions. The candidate failed the strict
total-floor improvement requirement (`234` is not greater than `234`), making
the full conjunction false. Production configuration was restored exactly and
no checkpoint was replaced.

## Next Step

Do not spend more live games on this frozen inventory-only candidate or create a
mechanical near-neighbor. The useful follow-up is a bounded trace-level review
of the five raw-action-divergent pairs, then a materially different training
hypothesis that can change decision quality rather than only reduce one-step
replay loss.
