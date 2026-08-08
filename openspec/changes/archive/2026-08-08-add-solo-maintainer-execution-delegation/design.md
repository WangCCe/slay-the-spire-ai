## Context

The cross-fitted successor currently accepts one approval schema. It requires
`provenance.source == external-human-message`, stores generated and human text
together in `verbatim_approval_text`, and requires the exact request digest to
appear in that text. The independent verifier reproduces the same contract.
This is correct for historical approvals but cannot honestly represent a broad
human delegation followed by a machine-resolved exact request.

Readiness r4 is bound to source commit `0570aa23...` and that commit's canonical
spec explicitly rejects standing permission. Therefore any real delegation
support changes both source and contract identity; r4 remains immutable
historical evidence and cannot register a successor under the new source.

## Goals / Non-Goals

**Goals:**

- Represent the human grant and machine resolution as separate canonical data.
- Make the complete delegation a transitive part of approval and authorization,
  so existing tracked-authorization preflight also binds it.
- Independently reject every request, delegation, scope, provenance, exclusion,
  resolution, or digest drift.
- Preserve validation of all historical v1 approval and terminal artifacts.
- Provide source-only CLI commands that validate a delegation and render the
  request-specific delegated approval and authorization without manual digest
  transcription.

**Non-Goals:**

- Reinterpreting or changing any historical approval, registration, terminal,
  readiness publication, or consumed identity.
- Claiming cryptographic human identity, bypassing Codex/platform approvals, or
  authorizing unrelated destructive operations.
- Registering, executing, fitting, training, evaluating, or changing the
  successor algorithm in this change.

## Decisions

### Add a closed standing-delegation v1 schema

`build_standing_delegation` will produce a canonical mapping containing:

- schema version and `delegation_sha256` over the body;
- exact grant text, grant timestamp, and external-human message/task provenance;
- repository scope expressed as pushed remote `origin/master` plus the exact
  cross-fitted successor registration-id prefix;
- exact request class equal to the successor execution-request schema version;
- a closed, sorted exclusion set covering host/OS approval bypass, bound-term
  mutation, unrelated destructive operations, and request substitution; and
- a fixed rule that a later explicit human revocation prevents future approval
  publication but does not rewrite already published evidence.

The scope is compared mechanically with the registration. It does not use an
absolute checkout path, so temporary-repository tests and equivalent local
checkouts remain valid.

Alternative: store only the original sentence and task id. Rejected because it
would not make repository, request class, exclusions, or revocation semantics
testable. Alternative: sign the delegation. Rejected because no key or identity
infrastructure exists and the project must not imply cryptographic identity.

### Embed the complete delegation in delegated-approval v2

`bind_delegated_approval` will validate the exact request and delegation, then
create a resolution with the request digest, delegation digest, fixed resolver
kind, and resolution timestamp. The approval contains the full delegation and
resolution, approval mode, approved request digest, schema version, and an
approval body digest. It contains no `verbatim_approval_text` and does not label
generated text as a human message.

The existing authorization embeds the complete normalized approval. Therefore
the authorization digest transitively binds the delegation bytes without adding
a terminal artifact or output-inventory entry. Source-only workflows may also
publish the delegation as a standalone tracked manifest for human inspection;
execution correctness does not depend on locating that sidecar because the
authorization contains the validated canonical copy.

Alternative: authorization stores only `delegation_sha256`. Rejected because a
digest without the manifest would make terminal verification depend on an
external sidecar. Alternative: add a new terminal file. Rejected because it
would change inventory and recovery semantics unnecessarily.

### Branch approval validation by schema and preserve v1

Producer and independent verifier will accept:

1. historical external-human approval v1 with its current exact rules; or
2. delegated-approval v2 with the new closed manifest and resolution rules.

Both routes return a normalized approval embedded by the unchanged authorization
schema. No v1 artifact is migrated. New source-only delegated workflows use v2;
the old helper remains available only for exact human approval and historical
tests.

### Add source-only rendering commands without execution authority

Add commands to inspect a delegation against a registration, render a delegated
approval from registration/request/delegation plus a supplied resolution time,
and render authorization from exact canonical inputs. They write canonical JSON
to stdout and never publish files, load Torch/native code, construct an
environment, or invoke execution. File publication and Git review remain an
explicit orchestration step.

### Require fresh readiness after the source commit

Control-plane, independent-verifier, tests, and canonical spec bytes change.
After this change is reviewed, committed, and pushed, a separate preregistered
readiness identity must bind that new source. Only a separately verified `go`
can enable another registration proposal. No r4 artifact is mutated or reused
as eligibility.

## Risks / Trade-offs

- **Dual schemas increase verifier surface** -> Keep exact schema dispatch and
  preservation fixtures; reject hybrids and unknown fields.
- **A malformed grant could appear broad enough** -> Require closed scope,
  request class, exclusions, provenance, and self-digest before resolution.
- **Embedding repeats manifest bytes** -> The manifest is small and removes an
  external terminal dependency; byte duplication is preferable to ambiguous
  trust.
- **Future user revocation is not discoverable from runtime or source-only
  rendering state** -> Approval-publication orchestration must recheck the
  current external conversation state before tracking generated bytes. The
  renderer grants no publication or execution authority; published
  authorizations remain immutable evidence and can be cancelled by never
  invoking them.
- **Another readiness cycle costs time** -> Accept the cost because executing
  under a contradictory source-bound contract is invalid.

## Migration Plan

1. Add RED producer, independent-verifier, CLI, tamper, hybrid-schema, import-
   isolation, and historical-preservation tests.
2. Implement the minimal closed schemas and CLI routing in the standard-library
   control plane and independent verifier.
3. Run focused tests, import probes, strict OpenSpec, independent review, and the
   repository commit gate once; fix only accepted source defects.
4. Sync the canonical spec, archive, commit, and push the clean source change.
5. In a separate change, preregister a new readiness identity for the new source.

Before push, rollback removes the additive implementation/spec/tests. After
push, corrections use a new source commit and readiness identity; historical v1
and r4 artifacts remain byte-identical.

## Open Questions

None. Revocation before approval publication is an external orchestration stop,
not a claim that source-only rendering can discover an unrecorded later human
message and not a reason to mutate an existing request or authorization.
