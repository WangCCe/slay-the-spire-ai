# Guard-Aware Counterfactual Audit

## Result

The current latent-gated candidate is not a reliable replacement for the
deployed guarded baseline on fresh replay states.

## Evaluation Aggregate

- Changed states: 990
- Raw-parent EndTurn share: 85.25%
- Configured exact agreement with guarded action: 30.71%
- Configured behavior-equivalent agreement: 31.92%
- Gate-open behavior precision: 40.97%
- Gate-open behavior precision over thresholds 0.50-0.95: 39.29%-41.41%

Duplicate card or potion slots are counted as equivalent only when item
identity, target, and encoded card features agree. This avoids treating
identical Strike copies as a policy difference.

## Decision

Do not tune the existing gate threshold or repeat its live gate. The next
training recipe must estimate advantage over the deployed guarded action,
rather than behavior-cloning that action and replacing the guard with an
imperfect imitation.
