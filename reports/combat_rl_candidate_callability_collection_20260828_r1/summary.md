# Combat RL Candidate Callability Collection R1

## Decision

The fresh production-r16 collection passes every pre-fit gate and is eligible
for the separately registered, single 64-update CPU development fit. It grants
no gameplay, holdout, qualification, promotion, or production authority.

## Evidence

- 10/10 registered seeds completed in order; no game 11 started.
- Replay schema v3 contains 1,634 legal transitions: 186 direct proposals,
  446 changed same-state proposals, 1,002 no-proposal takeover rows, and zero
  legacy-unknown rows.
- Production r16 online and target parameters are unchanged, optimizer state is
  empty, and all 186 direct actions match frozen eval-mode r16.
- The candidate SMDP has 632 decision spans across 126 combats. All 1,634
  source rows reconcile as decisions, attached takeover rows, or uncontrolled
  prefixes. Both train and validation partitions contain direct and changed
  proposal strata.
- A 1:1 trace join has zero action-family, hand, potion, or relic tensor
  mismatches and zero cross-floor nonterminal transitions.

## Audit Correction

The original runner incorrectly required an immediate post-action `next_*`
snapshot to equal the next settled candidate-decision state. Twenty-nine of
536 nonterminal boundaries legitimately differ while card effects, enemy turns,
or draws settle. Commit `ab68e1204` aligns the implementation with the frozen
design: nonterminal spans bootstrap from the next proposal-bearing row. No fit
was started and no recipe, seed, threshold, or gate changed before this fix.

## Limitations

- All 10 runs lost; mean floor was 19.4. Outcome quality was not a registered
  gate for this training-only corpus.
- The internal card id `Ghostly` (Apparition) maps to the existing unknown card
  id in 111 joined states. Trace and replay agree, but this remains a separate
  state-representation limitation.
