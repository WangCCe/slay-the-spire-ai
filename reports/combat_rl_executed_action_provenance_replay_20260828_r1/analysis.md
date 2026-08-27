# Executed-Action Provenance Replay R1

## Result

The registered ten-game collection completed all seeds in order and retained
1,451 replay transitions. No optimizer update occurred: online and target
weights remain byte-equivalent to production r16, optimizer state is empty,
and `learning_starts=100000` remained above the replay count. All 1,451 stored
actions are legal, and there are no cross-floor nonterminal successors.

The provenance implementation itself passes the fresh evidence check. The
checkpoint contains 1,212 override rows and 239 direct rows. Runtime telemetry
contains 624 RL proposals; the other 827 eligible emitted actions occurred
during takeover without a fresh RL proposal. The counts reconcile exactly:

- `1,212 = 827 no-proposal actions + 385 changed proposals`
- `239 = 624 proposals - 385 changed proposals`

The 491 replacement messages are supporting guard telemetry rather than a
second row count: some replacements happen after takeover has already started.
The retained logs also contain 778 continuing-takeover messages and 197
fallback-action repairs, with no traceback or RL action failure.

## Training Decision

Do not train from this cohort yet. Of the 239 rows emitted directly from an RL
proposal, 44 differ from the frozen r16 eval-mode greedy action. The collection
uses `--train` to persist replay, which leaves the online dueling network in
train mode during `select_action()`; its hidden Dropout layer therefore remains
active even at epsilon zero. Production `--eval` explicitly puts the network in
eval mode.

This does not invalidate the new provenance flag: those 239 actions were still
direct proposals and correctly remained unmarked. It does mean the cohort is
not deployment-consistent enough to become the first provenance-aware training
corpus.

## Next Step

Use a separate OpenSpec change to run the online network in eval mode only for
behavior action selection, restoring its previous mode immediately afterward
so optimizer updates retain current training semantics. Then collect one new
bounded zero-update provenance cohort. Start provenance-aware candidate fitting
only if direct unmarked actions match frozen r16 eval-mode greedy decisions and
override legality/reconciliation remain clean.
