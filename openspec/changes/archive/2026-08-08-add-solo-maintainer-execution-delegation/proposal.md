## Why

The solo maintainer has delegated repository execution decisions to Codex and
asked not to transcribe long generated authorization tuples. A reviewed
compatibility attempt proved that encoding an agent-generated resolution as the
legacy `external-human-message` would violate the source-bound successor
contract, so standing delegation must become an explicit producer- and
verifier-enforced schema before any new readiness or empirical registration.

## What Changes

- Add a canonical standing-delegation manifest that preserves the exact external
  human grant, message/task provenance, repository and request-class scope,
  exclusions, revocation rule, and its own content digest.
- Add delegated-approval v2. It embeds the complete validated delegation,
  mechanically binds its digest and the exact execution-request digest in a
  request-specific resolution, and is embedded unchanged in authorization.
- Preserve historical external-human approval v1 validation for already
  registered and terminal evidence. New delegated approvals no longer use the
  misleading `verbatim_approval_text` or claim that generated text was typed by
  the user.
- Extend the independent terminal verifier and source-only CLI/tests to
  reconstruct all delegation, approval, request, authorization, and scope
  bindings without trusting producer output.
- Keep pushed source, tracked-blob, native-before-Torch, isolation, atomic claim,
  durable journal, resource, retry, and terminal rules unchanged.

Live evidence is the independent review finding that the untracked compatibility
artifacts contradicted source commit `0570aa23...`; those artifacts were removed
before publication and no output root or empirical operation was created.
Success is a clean pushed source change whose RED/GREEN control and independent-
verifier tests prove valid delegated approval, fail-closed tampering, historical
v1 preservation, and import isolation. A later fresh readiness attempt is a
separate change and identity.

Non-goals are reusing r4 eligibility for changed source, registering a successor,
publishing execution authority, loading native/model dependencies, constructing
an environment, accessing seeds, fitting, training, evaluation, OPE, gameplay,
CommunicationMod, qualification, promotion, or changing the learning experiment.
Before commit, rollback removes only this additive source/spec/test change. Once
pushed, historical approval artifacts remain immutable and any correction uses a
new source identity; it never rewrites old evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-cross-fitted-hierarchical-learning-successor`: Define canonical
  standing delegation and delegated-approval v2 as an exact alternative approval
  mode while preserving historical v1 evidence and every execution boundary.

## Impact

- Changes the cross-fitted successor standard-library control plane, independent
  verifier, focused control/verifier tests, canonical successor spec, and project
  direction.
- Invalidates r4 as registration eligibility for the new source, requiring a new
  preregistered readiness attempt before any successor registration.
- Does not change Torch runtime, native adapter, simulator, model/checkpoint,
  CommunicationMod configuration, or gameplay behavior.
