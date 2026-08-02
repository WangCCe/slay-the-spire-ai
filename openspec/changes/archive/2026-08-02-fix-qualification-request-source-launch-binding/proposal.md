## Why

The retired r8 live boundary reached `source_verified` and then failed request validation because the published qualifier command passed the absent active-request path to `--request` instead of the committed `request_source_path`. The existing offline review checked request bytes and launcher shape but did not bind that command argument semantically, so a valid request and invalid launch vector could pass preparation independently.

## What Changes

- Add one canonical qualification launch-command builder that derives `--registration`, `--request`, request anchors, and review commit from the reviewed request contract and always uses `request_source_path`.
- Add an offline validator for a rendered qualification launch vector and fail closed when `--request` names the active publication path, differs from the reviewed source path, or any ordered anchor differs.
- Route the production-Python no-action smoke through the canonical builder and add a frozen r8-shaped regression covering the source/active path distinction.
- Record a read-only r8 diagnosis while preserving the retired r8 root and historical artifacts byte-for-byte.
- Success means the r8-shaped wrong vector is rejected before publication, the canonical vector passes focused tests and the registered commit gate, and no live/external qualification identity, game, study, or training process is started. Isolated temporary-directory smoke children remain permitted test fixtures.
- Non-goals are retrying r8, preparing r9, changing bootstrap/request schemas, changing gameplay policy or rewards, collecting trajectories, computing OPE, or training.
- Rollback is deletion of this unarchived change and its narrow source/test/report edits before any later replacement amendment; no live state or historical qualification evidence is mutated.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-outcome-evidence-expansion`: Require the qualifier launch vector to bind `--request` to the reviewed request source rather than the not-yet-published active request.
- `pre-request-qualification-observability`: Require offline preparation and go/no-go review to derive and semantically validate the exact launch vector before publication.

## Impact

- Affected code: `scripts/run_noncombat_outcome_evidence_expansion.py`.
- Affected tests: focused qualification runner regressions and the production-Python no-action smoke.
- Affected evidence: one new diagnosis report; existing r8 request, checklist, publication, root, and closeout bytes remain unchanged.
- Dependencies and gameplay behavior are unchanged.
