## 1. Regression Evidence

- [x] 1.1 Add a RED outer-agent regression reproducing a multi-monster target-lethal guard attack replaced by a defensive candidate.
- [x] 1.2 Add controls proving lethal-to-lethal replacement and ordinary nonlethal takeover remain eligible.

## 2. Narrow Safety Fix

- [x] 2.1 Add a deterministic target-lethal action predicate using existing combat damage, target, block, modifier, and hit-count helpers.
- [x] 2.2 Pass the completed guard action into the candidate safety decision and emit `mandatory_guard:target_lethal` only for lethal-guard-to-nonlethal-candidate replacement.

## 3. Qualification And Closeout

- [x] 3.1 Run focused action-relative and combat guard tests, Python compilation, and strict OpenSpec validation.
- [x] 3.2 Run exactly one timed repository commit gate, review the scoped diff, and commit/push the qualified behavior class.

  The single commit gate passed 4,330 tests with 26 skipped and 21 deselected
  in 203.00 seconds (206.55 seconds runner elapsed). The complete
  action-relative candidate file accounted for 0.84 seconds; its timing report
  is retained for the separate gate-duration audit.
- [x] 3.3 Record that standalone live replay is intentionally deferred: production r16 does not enable candidate authority, the matched cohort is closed to retry, and the next separately preregistered candidate gate must retain this fixed policy.

  Production r16 has no action-relative candidate authority enabled, and the
  2026-08-29 matched cohort is closed to retry or reinterpretation. The next
  separately preregistered candidate gate must bind this fixed safety policy;
  no standalone gameplay replay is justified for this source-only fix.
