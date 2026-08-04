## Context

The closed r2 experiment projects exact API v3 snapshots and candidates through
a recursive leakage filter, hashes the projected state and candidate values,
and adds the shared state vector to every candidate row. Its linear scorer
therefore cannot use state-only values to change relative candidate ordering.

`StateConditionedCandidateRanker` now accepts separate state and candidate
tensors, and `summarize_policy_diagnostics` can report candidate availability,
selection saturation, and score margins. Neither capability is connected to a
validated simulator policy-input boundary. The integration must remain
development-only and must not modify the source files bound to the terminal r2
experiment.

## Goals / Non-Goals

**Goals:**

- Produce deterministic separate state and candidate tensors from exact API v3
  inputs with the existing recursive leakage exclusions.
- Bind a stable policy-input identity for future registrations.
- Construct canonical scored-decision rows accepted by the existing diagnostic
  summarizer.
- Prove the integrated boundary is state conditioned, order equivariant,
  fail-closed, and source preserving.

**Non-Goals:**

- Editing or rerunning r2, loading the native simulator, accessing seeds, or
  constructing an environment.
- Adding a training or evaluation runner, optimizer, reward, checkpoint, or
  production-agent integration.
- Establishing Current structural closure, a credible baseline floor,
  target-supported outcomes, formal-RL readiness, or policy quality.
- Treating SimpleAgent, Bottled, or seeded initialization as a primary policy
  comparator.

## Decisions

### Add one isolated policy-input module

Create `analysis_scripts/noncombat_state_conditioned_policy_input.py`. It will
import the existing API v3 projection and stable feature encoder, but it will
not call or modify `candidate_feature_matrix_v2`. This keeps the r2 evidence
identity intact and makes the new semantics explicit.

Alternative considered: edit the r2 experiment in place. Rejected because the
experiment is terminal and hash-bound, and because an empirical runner should
not be the first test surface for the architecture repair.

### Encode state and candidates independently

Project every candidate with `project_policy_view_v2`, require the projected
state to be identical for the whole decision, encode that state once, and
encode each candidate against an empty state mapping. Return CPU float32 tensors
with shapes `[hash_dim]` and `[candidate_count, hash_dim]`.

Alternative considered: add explicit pairwise cross features. Rejected for this
change because the nonlinear ranker already supplies interaction capacity and
separate channels preserve the existing feature vocabulary with less new code.

### Version the boundary, not the old encoder

Publish stable metadata for policy-input schema, projection version, feature
version, hash width, dtype, device, and ranker architecture identity. The new
feature version identifies separate-channel composition even though the
underlying deterministic hash primitive is reused.

Alternative considered: expose only raw tensors. Rejected because future
registrations need a compact identity surface and must fail on composition
drift.

### Build diagnostic rows without policy authority

Add a helper that validates one decision identity, category, candidate list,
score vector, and selected index, then emits the exact standard-library
diagnostic row shape. Candidate order remains the caller's order for score
association, while action IDs provide stable identity to the summarizer.

Alternative considered: integrate diagnostics directly into an experiment
runner. Rejected because no new experiment is authorized and the row contract
is independently testable.

### Keep import and execution boundaries explicit

The module may import Torch because tensor construction and the ranker already
depend on it. Tests must prove that importing and invoking the projection does
not import the native adapter, SpireComm coordinator/action modules,
Communication Mod, gameplay entry points, or checkpoint loaders.

## Risks / Trade-offs

- [Hashed state and candidate channels can still collide internally] -> Retain
  the existing 1,024-width deterministic signed hash and bind its identity;
  changing representation quality belongs to a later evidence-backed change.
- [Importing the r2 module could accidentally activate runtime behavior] -> Use
  only its pure projection function and add fresh-process import-isolation
  coverage for native and gameplay modules.
- [Candidate scores can be paired with the wrong action after reordering] ->
  Validate exact score count and selected index, preserve positional pairing,
  and test candidate permutation end to end.
- [A passing state-reversal regression could overstate policy quality] -> Keep
  all authority false and state explicitly that the test proves capacity only.
- [Future edits to the reused projection can change new input semantics] ->
  Expose dependency identities for future hash binding; do not copy or fork the
  leakage list in this change.

## Migration Plan

Add the module and regressions without importing it from production or existing
experiment paths. Verify focused tests, import isolation, the unchanged r2
verifier, the registered commit gate, and strict OpenSpec validation. Rollback
removes only the additive files and spec; no data or model migration is needed.

## Open Questions

None. Comparator execution, fresh cohorts, and formal training remain separate
future decisions.
