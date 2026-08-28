## Context

The r3 LightSTS guard-transfer POC trained a 64-unit gate and legal action head from fixed simulator and development-replay data. It passed a first independent replay, and the exact recipe later passed a separately collected fresh replay. The committed `LatentGatedActionAdapter` now provides the frozen-parent runtime and artifact contract, but no source-bound runner creates a durable candidate from that evidence.

Older successor runners combine useful identity checks with one-shot authorization supplements and no-retry receipts. Those controls are disproportionate for this single-owner development repository and slow down iteration without improving the scientific separation between fit and evaluation data.

## Goals / Non-Goals

**Goals:**

- Reproduce the supported POC recipe as one deterministic CPU development fit.
- Bind code, native module, item data, parent, development replay, and evaluation replays by SHA-256.
- Keep simulator pretraining, development fitting and threshold calibration, and evaluation replay scoring visibly separate.
- Produce a strict non-production adapter artifact and an atomic report with enough telemetry to reproduce or reject the candidate.
- Permit an unchanged rerun after an infrastructure failure while preventing silent in-place tuning after a scientific failure.

**Non-Goals:**

- Modify the RL v2 parent, agent routing, CommunicationMod configuration, or production r16.
- Add TD or reward optimization to the correction heads.
- Launch the game, train online, qualify, promote, or claim live policy improvement.
- Generalize the first runner into a broad experiment framework.

## Decisions

### Use one committed registration instead of an execution supplement

The registration will contain the fixed recipe, fixed technical gates, exact input paths and hashes, output path, source commit, complete behavior-affecting source inventory, and development-only authority. The runner requires the registration itself to match committed HEAD content, validates every listed source against the registered ancestor commit and current worktree, rejects development/evaluation replay overlap, permits no external DLL directory for this self-contained module, and refuses an existing output directory.

This preserves source binding while removing per-command external approval text, a separate binding supplement, and a started receipt. An infrastructure failure may be rerun with the same registration after the partial staging directory is removed; a completed scientific failure is immutable and requires a new preregistered change to alter the recipe.

### Reproduce the supported two-stage recipe

The gate head is initialized from 128 fixed LightSTS balanced updates and refined for 128 balanced updates on the development replay. The legal action head receives 256 changed-row updates from the development replay only. Batch size, learning rate, seeds, simulator seeds, and battle indices are fixed to the confirmed r3 recipe.

The gate threshold is calibrated only on development rows by maximizing changed-row recall subject to a 10% direct-row open cap. The final adapter is rebuilt with that threshold and exact fitted head states before serialization.

Alternatives considered:

- Joint gate/action training through the generic adapter loss was rejected for this first artifact because it would differ from the twice-confirmed POC recipe.
- Adding TD loss was rejected because the prior residual cohort showed that TD improvement did not establish intervention selectivity.

### Require every bound evaluation replay to pass fixed gates

Evaluation checkpoints are read only after fitting and never contribute gradients or threshold calibration. Each must independently satisfy: direct open share at most 0.15, changed open share at least 0.75, direct candidate agreement at least 0.85, changed raw correction agreement at least 0.35, changed candidate agreement at least 0.25, overall agreement uplift at least 0.10, and no increase in positive-energy EndTurn selections.

The report distinguishes per-replay checks from the aggregate decision. One failed replay makes the candidate ineligible for gameplay registration.

### Serialize only the adapter and immutable provenance

The runner uses `build_development_artifact` and immediately restores the artifact against the exact parent. It requires exact action, correction-action, gate-probability, and telemetry parity over development plus evaluation rows. The artifact remains marked non-production-compatible.

Output is restricted to a new child under the repository `reports/` directory, written through a staging directory, and atomically renamed only after the report and round-trip checks succeed. The registration bytes are read and hashed once before execution so the report cannot acquire a different registration identity during a long run. No checkpoint or source input is modified.

## Risks / Trade-offs

- [Simulator labels encode a guard proxy rather than game truth] -> Require both independent real replays to pass and keep gameplay as a separate downstream gate.
- [The fixed recipe may overfit the small development replay] -> Keep both evaluation replays isolated and require each one to pass rather than pooling metrics.
- [Reusing POC helpers could couple production code to exploratory classes] -> Keep reusable runtime behavior in `latent_gated_adapter`; the runner may reuse pure corpus/metric helpers but owns artifact creation and source validation.
- [Allowing infrastructure retry can obscure repeated failures] -> Never overwrite output, record the exact registration/run identity, and prohibit recipe changes without a new registration.
- [Large LightSTS collection cost] -> Use the already confirmed 256-seed bounded cohort and no hyperparameter search.
