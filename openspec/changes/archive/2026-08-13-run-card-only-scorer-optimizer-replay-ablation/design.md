## Context

Checkpoint `004` contains the current card policy and four-step Adam state. The
next live chunk is deterministic for the bound model/generator/native identity,
but repeated mechanism experiments currently pay the native rollout cost again
because trajectories are not durably replayable. An optimizer update only needs
ordered decision identities/categories, state features, card candidates and
features, selected actions, rewards, terminal metadata, and the post-collection
generator states.

## Goals / Non-Goals

**Goals:**

- Encode and decode the exact data required to rebuild cross-fitted baselines and
  branch-local card policy terms without native environment access.
- Prove replay losslessness through exact reproduction of historical checkpoint
  `005` model, optimizer, and bootstrap state.
- Compare full-model Adam with a scorer-only Adam that inherits exactly the
  scorer parameter moments and options from checkpoint `004`.
- Make the replay reusable for later source-bound offline mechanism analysis.

**Non-Goals:**

- Training more than one optimizer step per branch.
- Evaluating outcomes after either update, selecting a gameplay policy, or
  accessing fresh/protected cohorts.
- Rescaling the scorer learning rate or changing objective/reward semantics.
- Serializing autograd graphs, full gradient vectors, transitions, or native
  environment objects.

## Decisions

### Use canonical JSON in deterministic gzip

Each supported episode is represented by ordered scalar metadata and canonical
CPU float32 tensor payloads. The replay is canonical JSON compressed with fixed
gzip metadata and carries stored/uncompressed SHA-256 and size bindings. Decode
is bounded before parsing and re-encoding must reproduce exact stored bytes.

Dense tensor encoding is retained initially because the existing codec already
has strict dtype/shape/finite validation and gzip compresses the predominantly
zero feature vectors. A sparse custom codec is deferred unless the registered
stored-size ceiling is exceeded.

### Apply post-collection generator state to decoded branches

The artifact records every bootstrap generator after live collection. Decoded
branches restore those generator states before updating, while model and
optimizer remain at checkpoint `004`. This permits branch A bootstrap and Adam
state to reproduce historical checkpoint `005`, not only its model bytes.

### Slice Adam state by exact parameter identity

Branch B includes only `family_head.scorer.*` and
`conditional_ranker.scorer.*`. A new Adam instance uses the registered options,
then receives the corresponding moment entries from the full optimizer state by
ordered parameter identity. Hidden parameters are absent from its optimizer and
must remain byte identical after the step.

### Gate on retained function movement

Both branches use identical replayed trajectories and current clipped baseline
semantics. Scorer-only is material only when it retains at least `0.80` of the
full branch's mean joint total variation from entry, the full movement is
positive, hidden bytes remain exact, and neither branch collapses. The gate may
propose a separate four-step experiment but authorizes no continuation.

## Risks / Trade-offs

- [Replay artifact may be large] -> Cap stored bytes at 64 MiB and canonical
  bytes at 512 MiB; fail before optimizer steps if exceeded.
- [Decoder could silently alter order or float values] -> Require exact
  round-trip bytes and full branch model/optimizer/bootstrap reproduction.
- [Sliced Adam mapping could select wrong moments] -> Bind ordered parameter
  names and add reverse tests for missing, reordered, or hidden parameters.
- [One-step retained TV may not imply outcome quality] -> Authorize only a
  four-step proposal, never fresh evaluation or promotion.
- [Historical checkpoint includes experiment bookkeeping] -> Compare bootstrap
  and optimizer state exactly; compare behavior-runtime coordinates separately.
