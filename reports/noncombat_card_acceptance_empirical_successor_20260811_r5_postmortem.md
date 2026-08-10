# R5 Card-Acceptance Inventory Postmortem

## Outcome

R5 built and independently verified a compact v4 inventory, but it is terminal
without registration. The hardened source-only verification and standalone
standard-library verifier agreed on the 255,499-byte artifact, 828 sources,
6,821 excluded seeds, fixed `512/128/512` cohorts, and inventory digest
`deecb81010b76b4fbd197bef1eb732577481ae01591b9fa1a92b0428fe0526f3`.

During the subsequent registration-schema investigation, a broad text search
over `reports` and `openspec` emitted partial content from the protected r3 and
r4 `seed_inventory.json` files before failing with Windows error 1450. This is
predecessor inventory content access under the preregistered fail-closed rule.

## Lifecycle

- Build invocation count: 1; no retry or reinvocation.
- Source-only verification invocation count: 1; exit 0 in 286.6 seconds.
- Standalone verification: passed with no producer or runtime import.
- Registration: absent and permanently denied for the r5 identity.
- Parent tasks 6.2 and 6.3: unchanged and incomplete.
- Native/model/environment/gameplay/training/evaluation/OPE: not performed.
- Gameplay validation: not applicable.

The owning gate evidence remains 265 passed. The reused full gate evidence
remains 5,803 passed and 18 skipped because r5 changed no code or test behavior.

## Resolution

Preserve the r5 build and dual-verification artifacts as historical evidence,
preserve all predecessor bytes, and archive r5 as terminal. Recovery requires a
distinct reviewed successor identity with a content-blind registration path.
That successor must use targeted source/schema reads and must not scan report
roots that contain protected predecessor inventories.
