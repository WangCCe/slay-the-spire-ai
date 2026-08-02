## 1. Contract Regressions

- [x] 1.1 Add lexical-mask fixture tests for line comments, block comments, escaped ordinary strings and characters, equal layout/newline preservation, unsupported raw strings, and unterminated comments or literals.
- [x] 1.2 Add C++ case regressions proving commented case labels, returns, display outputs, numeric effect cases, conditions, and `eventData` references contribute no semantic evidence while raw case hashes and spans remain bound.
- [x] 1.3 Add strict predecessor-delta tests that allow only registered semantic-field changes and reject event, alias, status, authority, resolver-readiness, or unaccounted-alias drift.

## 2. Minimal Parser Correction

- [x] 2.1 Implement the deterministic layout-preserving C++ comment masker with field-specific fail-closed errors.
- [x] 2.2 Route function/case discovery and semantic summaries through masked source while retaining exact raw case text for provenance hashes and line spans.
- [x] 2.3 Implement a registration-bound, deterministic r1-to-r2 artifact comparator and atomic delta report without adding files to either canonical audit directory.

## 3. Superseding Registered Evidence

- [x] 3.1 Commit the reviewed implementation boundary, then create fresh r2 audit and delta registrations bound to the exact implementation, unchanged Current/upstream identities, immutable r1 evidence, expected semantic removals, and all-false authority.
- [x] 3.2 Publish r2 once without native or gameplay execution, run the registered predecessor comparison, and strictly recompute both outputs byte-for-byte.
- [x] 3.3 Confirm the same 25 events, 47 aliases, `24 source_complete + 1 source_partial`, zero unaccounted aliases, and exactly the registered removal of the four comment-derived display entries.
- [x] 3.4 Write the r2 closeout and update project direction to supersede r1 labels while preserving its files and all resolver, evaluation, and training blockers.

## 4. Verification And Closeout

- [x] 4.1 Run focused audit pytest with an isolated writable basetemp and strict validation of this OpenSpec change.
- [x] 4.2 Run global OpenSpec validation and the repository commit test gate; do not launch gameplay or run an unregistered native simulator path.
- [x] 4.3 Sync the modified capability spec, archive the completed change, commit cohesive artifacts, and push `master`.
