## Context

The development adapter is bound to the production-r16 parameter state and passed two isolated replay evaluations, but its action disagreement remains too large for direct activation. RL v2 currently loads one checkpoint and emits its selected action without a candidate-observation hook. The first live step therefore needs to measure the candidate on the exact states seen by production while guaranteeing that CommunicationMod receives the original parent action.

The repository has accumulated overly elaborate one-shot execution protocols. This change keeps scientific identity explicit through one committed registration, but uses normal process retry and focused tests. It adds no online fitting, mutable checkpoint, or control-plane service.

## Goals / Non-Goals

**Goals:**

- Load the exact candidate artifact only after the exact production parent checkpoint has loaded.
- Verify candidate, checkpoint, metadata, and parent parameter identities before gameplay starts.
- Evaluate the adapter on the same encoded state and legal-action mask used by RL v2.
- Preserve the parent-selected action byte-for-byte at the agent boundary.
- Produce bounded JSONL telemetry and a deterministic summary that can support a matched-gameplay go/no-go decision.
- Keep initialization and per-decision latency small enough for CommunicationMod.

**Non-Goals:**

- Let the candidate select gameplay actions.
- Train or tune either parent or adapter during the shadow cohort.
- Modify the production checkpoint, game protocol, or non-combat policy.
- Infer candidate policy quality from disagreement telemetry alone.
- Introduce another external approval, receipt, or no-retry framework.

## Decisions

### Use one committed, opt-in shadow registration

`STS_COMBAT_RL_LATENT_SHADOW_REGISTRATION` points to a tracked JSON registration. The registration binds the source commit, candidate artifact path and SHA-256, production checkpoint path and SHA-256, expected parent parameter hash, trace path, event budget, and readiness gates. Startup rejects an untracked or worktree-modified registration, any behavior-affecting source file that differs from the registered ancestor commit, a path/hash mismatch, a training or exploratory agent, or an output path outside the repository `reports/` tree.

This is preferable to several loose environment variables because one file is reviewable and reproducible. It is lighter than prior execution supplements because ordinary retries are allowed and there is no external receipt protocol.

### Initialize shadow after normal checkpoint restore

`RLAgentV2` continues to construct and load its parent exactly as before. Only after `load_model` succeeds does the optional runtime hash the current parent state and load the development adapter. The adapter loader checks its embedded simulator-parent checkpoint identity while the registration separately checks the actual production checkpoint bytes and common parent parameter identity.

This supports the existing development artifact without relabeling it as production-compatible. Copying its heads into a production checkpoint was rejected because that would blur shadow and promotion authority.

### Observe only deterministic parent decisions and bind the final emitted action

Shadow initialization requires inference mode, epsilon zero, and expert mix disabled. On each legal combat decision the runtime receives the already encoded tensors, action mask, and selected parent index, then computes the adapter selection without publishing yet. The existing outer `commit_executed_action` callback supplies the final guard-processed action for the same game state; the runtime then writes parent/correction/candidate/executed indices, proposal-change and candidate-match labels, gate probability, gate state, legality, parity, latency, and compact game context.

The returned RL proposal is decoded from the original selected index before or independently of shadow telemetry. The shadow hook has no return value and no route to replace either the proposal or the outer guard-processed action.

### Isolate post-start shadow failures from gameplay

Binding failures abort configured startup because evidence collected under the wrong identities is unusable. Once gameplay is running, inference or trace-write failures are logged, the shadow is disabled for the process, and the parent action continues. A best-effort error event is appended when the trace remains writable. The summary treats any error, sequence gap, parity mismatch, illegal candidate, or event-budget violation as not ready.

This separates evidence integrity from gameplay availability. Letting an exception reach the existing agent fallback was rejected because it could replace a valid parent action with `EndTurnAction`.

### Summarize fixed readiness checks without policy claims

A read-only summarizer validates registration, source, trace, event-schema, action-set, and derived-field identities; counts contiguous decision events; and reports parent parity, legal candidate/final-action rates, error count, gate-open/disagreement shares, and adapter-inference latency percentiles. Readiness requires the registered minimum decisions, exact parity and legality, zero errors, and inference latency below the registered ceiling. End-to-end CommunicationMod delay is reconciled separately from live logs. The report authorizes only consideration of a separately bounded matched gameplay gate.

## Risks / Trade-offs

- [Shadow inference and synchronous publication add decision latency] -> Preregister an adapter-inference p95 ceiling and separately reconcile full action delay from fresh CommunicationMod logs.
- [A write failure can leave no terminal marker] -> Log the failure, disable shadow, and require contiguous events plus run/log reconciliation before accepting the cohort.
- [The parent file and simulator-parent file differ while parameters match] -> Bind both the active production file identity and the adapter's embedded parent identity, then require the shared parameter-state hash.
- [A high disagreement rate may reflect out-of-distribution states] -> Report disagreement by act, floor, and room type; do not infer policy quality or activate the candidate.
- [Normal retry could mix source or session identities] -> Bind behavior-affecting source files, validate every existing event before append, continue the global event budget, and require contiguous per-session sequences. A normal reset with a pending proposal emits an error; a hard stop can omit at most the pending decision and therefore still requires run/log reconciliation.

## Migration Plan

1. Land the optional runtime and focused tests with no environment variable configured; default behavior remains unchanged.
2. Commit a bounded registration for the qualified development artifact and production r16.
3. Set the environment variable for a fresh r16-only cohort, collect traces and game/log evidence, then summarize.
4. Unset the variable to roll back immediately. Candidate action authority requires a later OpenSpec change or explicit matched-gate implementation.

## Open Questions

- The first cohort size and latency ceiling will be fixed in its registration after measuring focused local inference overhead; they are evaluation parameters, not runtime API defaults.
