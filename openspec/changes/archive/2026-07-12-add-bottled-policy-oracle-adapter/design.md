## Context
The current repo is the live gameplay, trace, evaluation, and RL-readiness platform. `bottled_ai` has a cleaner hand-authored policy framework with Ironclad `REQUESTED_STRIKE` handlers for the target non-combat surfaces. The existing comparator already contains locally encoded Bottled-style behavior, but the next step is to use the local Bottled checkout as the reference oracle where feasible.

## Goals
- Evaluate current shop, card-reward, event, and route samples against the local Bottled `REQUESTED_STRIKE` policy.
- Keep the adapter offline-only and read-only.
- Preserve existing sample normalization, outcome join, and report gates.
- Make oracle confidence explicit: native Bottled, Bottled-style fallback, unsupported, partial, or error.
- Include enough source metadata to reproduce a report against a specific Bottled checkout.

## Non-Goals
- No live gameplay policy replacement.
- No CommunicationMod `config.properties` edits.
- No formal non-combat RL training.
- No combat policy replacement; combat is feasibility-only in this change.
- No vendoring or modifying `bottled_ai`.

## Decisions
- Add a separate adapter module rather than importing Bottled directly inside live agent code.
- Resolve Bottled repo path from an explicit CLI option first, then environment variable, then the known local default.
- Prefer native Bottled handler execution through a narrow state shim for each supported screen. If a sample cannot be represented accurately enough, return an unsupported or partial oracle result instead of inventing a high-confidence label.
- Keep the existing locally encoded Bottled-style logic as a fallback and comparison baseline, but label it separately from native Bottled oracle output.
- Map Bottled commands back to normalized candidate action ids before using them in samples or reports.

## Alternatives Considered
- Replace current policy with Bottled directly: rejected because it would discard live trace/RL infrastructure and change gameplay before evidence is gathered.
- Keep only the current locally encoded Bottled-style comparator: rejected because it can drift from `xaved88/bottled_ai`.
- Fork or vendor Bottled into this repo: rejected because the goal is read-only oracle comparison and reproducibility against an external checkout.

## Risks
- Bottled handlers may depend on `GameState` methods not present in current trace samples.
  Mitigation: use category-specific shims and mark missing context as unsupported or partial.
- Route decisions may need full map semantics.
  Mitigation: implement route after shop/card_reward/event, and keep route confidence conservative when path context is incomplete.
- Command-to-candidate mapping may be ambiguous.
  Mitigation: preserve raw command, normalized label, mapped action id, and limitations.
- Bottled checkout may be missing, dirty, or unavailable.
  Mitigation: report source status and avoid native high-confidence labels when metadata cannot be collected.

## Verification
- Focused unit tests for path resolution, metadata capture, command mapping, and each non-combat category.
- Regression tests proving existing Bottled-style comparator behavior is still available.
- CLI smoke test producing a current-vs-Bottled report from fixture or trace samples.
- Guard test proving live config and training entrypoints are not modified by the adapter.
