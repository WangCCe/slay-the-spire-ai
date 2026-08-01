## 1. Conservative Signature Contract

- [x] 1.1 Add focused red tests proving comparable complete rows group only when every adapter-relevant input is equivalent, while the existing exact-context ranker remains empty for those varied contexts.
- [x] 1.2 Add focused red tests proving that card offers, shop affordability, event branch thresholds and relic flags, route feature vectors, oracle modes, partial/fixture/lower-confidence rows, and retry duplicates cannot create false support.
- [x] 1.3 Define a versioned, deterministic normalized-signature payload and stable trace occurrence identity without changing the current full-context fingerprint contract.

## 2. Offline Comparator Diagnostics

- [x] 2.1 Preserve source-path or run identity when loading trace JSONL inputs, and deduplicate normalized-group support by independent decision occurrence.
- [x] 2.2 Implement category-specific normalized signatures and conservative eligibility/exclusion accounting for shop, event, route, and card-reward rows.
- [x] 2.3 Implement deterministic normalized review-group ranking that preserves member IDs, full fingerprints, occurrence identities, and a compact variation summary.
- [x] 2.4 Render a distinct diagnostic report section with signature version and exclusions while leaving “Most Worth Fixing” backed only by the existing exact-context repair gate.

## 3. Evidence And Verification

- [x] 3.1 Run the focused comparator tests with the repository writable-basetemp workaround and inspect deterministic output, grouping, exclusions, and strict-gate preservation.
- [x] 3.2 Run the full pytest suite with a writable basetemp; this offline-only change SHALL NOT launch or reconfigure live gameplay.
- [x] 3.3 Regenerate one comparator report from the fixed Round 279 fresh-trace cutoff, record whether a group is only diagnostic or warrants manual investigation, and keep gameplay code unchanged.
- [x] 3.4 Run `openspec validate add-normalized-decision-signature-audit --strict` and review the final diff for scope, including the absence of agent, training, checkpoint, and live-config changes.
