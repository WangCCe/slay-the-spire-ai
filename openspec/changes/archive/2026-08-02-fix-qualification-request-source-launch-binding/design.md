## Context

The qualifier intentionally has two request paths with different lifecycle roles. `request_source_path` is a committed repository file that the parent reads and reviews before publication; `request_path` is an absent path inside the qualification root that the parent creates only after request review and isolation validation. The r8 preparation rendered a structurally valid trusted-launcher vector but supplied `request_path` to the CLI `--request` argument. The bootstrap could therefore prove the launcher, runner, and source before the request loader failed on the absent file.

The current runner already rejects this path in source mode, and the existing production smoke manually supplies the correct source path. The missing control is a reusable builder and an offline semantic check over the exact rendered command.

## Goals / Non-Goals

**Goals:**

- Make one production helper the source of truth for the ordered qualifier CLI suffix.
- Bind `--request` to the reviewed `request_source_path` and prove it differs from the active `request_path`.
- Validate externally rendered command vectors before publication.
- Regress the exact r8 failure shape without touching its retired root or launching a process.

**Non-Goals:**

- Changing request-v3, bootstrap-v1, token, envelope, or result schemas.
- Retrying r8 or preparing a replacement identity.
- Launching CommunicationMod, Java, the game, a live/external qualification identity, or the study. Isolated temporary-directory smoke children remain permitted test fixtures.
- Changing decision policy, rewards, OPE, or training.

## Decisions

1. Add a pure canonical suffix builder next to the qualification request and launcher code. It receives an already parsed request plus reviewed file anchors and R, validates scalar shapes, requires distinct absolute source and active paths, and returns the exact ordered `qualify` argument tuple. This keeps command construction testable without invoking a process or consulting mutable live state.

2. Add a validator that compares a candidate suffix to the canonical tuple rather than maintaining a second parser with partially duplicated rules. A mismatch fails closed with a qualification runner error. The full launcher command can continue to prepend the existing fixed Python, launcher-code, runner, envelope, and token fields.

3. Route the production-Python smoke fixture through the builder. The smoke remains the integration proof that CommunicationMod-equivalent splitting preserves the vector and that the no-action lifecycle works.

4. Preserve r8 evidence. The regression uses the committed r8 request as read-only evidence or an equivalent fixture and proves that its published active-path suffix is rejected while a source-path suffix is accepted. Historical checklist/config/root bytes are not corrected in place.

5. Do not add the source path to the bootstrap envelope. That would require a schema migration and historical verifier compatibility work disproportionate to this preparation bug; the existing runner remains the live fail-closed backstop.

## Risks / Trade-offs

- [Risk] A future ad hoc publication could bypass the helper. -> The offline go/no-go specification requires validating the exact final command vector with the helper, and future replacement work must include that check in its reviewed evidence.
- [Risk] A pure builder could accept a syntactically valid but stale request. -> Existing source review, request file SHA/size, direct-child R, and live runner validation remain authoritative; this helper only closes the source-versus-active path gap.
- [Risk] Reusing the committed r8 request in tests could couple tests to historical absolute paths. -> Keep the regression read-only and assert only path-role semantics; unit fixtures cover portable behavior.
- [Risk] Runner-byte changes invalidate previous reusable gates. -> Run focused tests and the current registered commit gate; no historical qualification is reinterpreted.

## Migration Plan

1. Add the failing r8-shaped regression.
2. Implement the canonical builder and validator and route the smoke fixture through it.
3. Run focused qualification tests, strict OpenSpec validation, and the registered commit gate.
4. Record the diagnosis and archive this source-fix change after syncing specs.
5. Any future replacement amendment must derive and validate its exact final command with the new helper before publication.

Rollback removes the new helper, tests, and unarchived artifacts before any replacement amendment. No live rollback is required because this change performs no live/external publication or launch.

## Open Questions

None. A future replacement identity and its timing remain a separate go/no-go decision.
