## Context

`SimpleAgent._choose_event_option` is the event path inherited by the Current
`OptimizedAgent`. It contains explicit event-id alias sets, a shared risky-event
set, and branches that inspect option labels through keyword matching. The r2
Current bridge proved one narrow `Liars Game` semantic contract but stopped on
the next unsupported event, `The Cleric`. The registered Stage 2 seeds are now
consumed and cannot be used as an event discovery loop.

The relevant upstream semantics are split across `sts_lightspeed` sources:
event enums and names, save-file ids, legal-action masks, console display
labels, and event execution effects. The external checkout is intentionally
dirty, so the audit must bind both its parent commit and exact source bytes.

## Goals / Non-Goals

**Goals:**

- Discover the complete Current event alias surface from Python AST rather than
  from gameplay observations or duplicated hand-maintained branch counts.
- Map every discovered alias group to one registered canonical event and one
  upstream enum without duplicates or silent fuzzy matching.
- Record exact source spans and deterministic summaries for upstream identity,
  legal-action, display-label, and execution cases, including conditional or
  phase-sensitive signals.
- Publish canonical JSON and Markdown artifacts that distinguish source-surface
  completeness from resolver readiness and fail closed on parser ambiguity or
  identity drift.

**Non-Goals:**

- Defining or implementing a total event resolver.
- Claiming that console labels alone prove exact game semantics.
- Running native simulator episodes, Communication Mod gameplay, or any seed.
- Changing Current decisions, rewards, action/state spaces, models, readiness,
  promotion, or training authority.

## Decisions

### Bind an explicit audit registration

The input registers the audit implementation commit and source hash, the exact
Current event source, the external simulator parent/full-source identity, the
five selected upstream files and hashes, the canonical alias-to-enum registry,
expected output names, and all-false authority. Execution verifies every byte
before analysis and does not supply defaults.

Alternative considered: inspect whichever checkout happens to be present and
write an informal note. Rejected because results could not be reproduced or
distinguished after either Current or upstream source drift.

### Parse Current with Python AST

The audit locates `SimpleAgent._choose_event_option`, extracts the literal
`risky_event_ids` set and each top-level `event_id in {...}` branch in source
order, records source spans and AST hashes, and reports whether each branch
references `labels_for_selection`. A registered canonical mapping must cover
the discovered aliases exactly; unknown, duplicate, or stale aliases block the
audit.

Alternative considered: grep event names from the file. Rejected because it
would mix logging, comments, aliases, and unrelated string literals.

### Build source spans without compiling or executing C++

The audit reads the event enum/name tables and save-id map, then indexes
`case Event::<ENUM>` spans in legal-action, display-label, and execution
switches. It records return masks, option-index/label literals, `eventData`
references, and conditional signals as source evidence. Ambiguous spans or
unparsed dynamic constructs remain explicit blockers instead of being guessed.

This is a source-surface inventory, not an effect interpreter. A row is
`source_complete` only when all required cases are uniquely bound and displayed
indices cover the statically observed legal-index union. `source_partial`
preserves conditional, phase, or parsing gaps. `blocked` means identity or
mapping closure failed. None of these statuses authorizes resolver code.

### Canonical artifacts and recomputation

The tool writes configuration, inventory, summary metrics, report, and a
manifest using sorted canonical JSON and atomic replacement. Recompute mode
must produce byte-identical artifacts and must reject an output directory with
extra files.

## Risks / Trade-offs

- **C++ switch structure exceeds the bounded parser** -> Report the exact enum,
  file, and span as `source_partial`; do not broaden into a C++ parser or infer
  behavior.
- **Current aliases do not match save ids exactly** -> Require an explicit,
  duplicate-free canonical mapping in the hash-bound input.
- **A source-complete row is mistaken for resolver readiness** -> Keep a
  separate `resolver_ready=false` field and repeat the authority boundary in
  metrics, manifest, and report.
- **Dirty upstream checkout changes after registration** -> Bind the full
  source digest and each selected file hash; fail before parsing on drift.
- **Audit implementation perturbs runtime behavior** -> Keep it in
  `analysis_scripts`, import no native module, and add a test proving the
  gameplay agent source is read-only.
