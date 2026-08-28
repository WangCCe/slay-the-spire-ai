# Combat RL Provenance-Aware Successor R1

## Decision

`development_candidate_not_eligible_no_same_corpus_tuning`

The registered 256-update recipe completed exactly once and produced a finite,
round-trip-exact candidate. It passed the TD-fit, provenance-label, optimizer,
serialization, and positive-energy End Turn gates, but failed the fixed 15%
validation action-drift ceiling. Production r16 remains authoritative and this
candidate is not eligible for a fresh holdout, gameplay, qualification, or
promotion.

## Bound Evidence

- Source commit: `17c297f8d40715c60447e82971329d7dea552cf4`
- Input checkpoint SHA-256: `302a7350a7e216ea548025ac4cb588c1ea77872328ccef977f94feab65e03fb4`
- Candidate SHA-256: `1c97d4680f7e1c125738655274d332066a1cd12c644cad1fb299bc4d73dc67f3`
- Candidate state SHA-256: `a7f8a505f9816f12b87d35528ff6383051b03f8c2cd3c369a5db6b0036d4ae09`
- Split: 157 complete combat groups, 1,722 train transitions, 387 validation transitions
- Provenance: 466 direct rows and 1,643 executed-action override rows

## Result

- Whole-model relative L2: `0.0104696`
- Validation TD loss: `3.80083 -> 3.31689`
- Validation anchor-label agreement: `0.41344 -> 0.59432`
- Validation greedy disagreement: `236/387 = 60.98%`
- Direct-row disagreement: `20/77 = 25.97%`
- Override-row disagreement: `216/310 = 69.68%`
- Positive-energy End Turn: `206/295 -> 13/295`

Of the 236 validation changes, 205 are `End Turn -> PlayCard`; 203 of those
come from override rows. The candidate therefore learned the intended outer
guard signal, but the recipe also changed too many direct parent decisions.
The update is a substantial policy rewrite, not a marginal successor.

## Consequence

Do not rerun, shorten, or reweight this recipe on the r1 corpus. A future
attempt requires a new training corpus and a separately preregistered design.
That design should gate direct-parent drift separately from override-label
uplift and use a lower fixed update budget; the aggregate parent-disagreement
ceiling alone does not distinguish desirable guard absorption from unsafe
direct-policy drift.
