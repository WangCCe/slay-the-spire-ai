## 1. Source-Only Regression Foundation

- [ ] 1.1 Add RED control-plane and verifier import-isolation tests proving that control-only commands do not import Torch, load the native adapter, construct an environment, or access a seed.
- [ ] 1.2 Add RED metadata and source-binding tests for the three additive modules, public dependency inventory, immutable controls, all-false authority, and byte-preservation of consumed hierarchical evidence.
- [ ] 1.3 Add RED state-feature tests for exact-API-v3 validation, 1024-to-128 modulo folding, candidate independence, sparse float32 identity, prohibited-field leakage, malformed values, and deterministic replay.
- [ ] 1.4 Add RED fold and baseline tests for canonical `position mod 4` assignment, exact `16/48` held-out/fit identities, whole-trajectory isolation, float64-before-multiply trajectory-balanced normal equations, exact pre-clip prediction replay, fixed `1e-9 + 1e-9 * scale` ridge-residual boundaries, Cholesky-only failure, prediction clipping, and poor-fit no-fallback behavior.
- [ ] 1.5 Add RED advantage and objective tests for return-to-go bounds, fixed-unit residual arithmetic, absence of later normalization, exact five-component membership and denominator, graph-connected empty subsets, and preserved learning controls.
- [ ] 1.6 Add RED gradient tests for component/full reconstruction, signed cancellation, ledger versus consumed Torch clipping, exact installed float32 gradients, scalar loss reconstruction, consumed threshold-neighborhood legacy normalization, same-batch diagnostic metrics, wrong-gradient/missing-step/wrong-moment Adam replay rejection, zero-norm cosine, and fail-closed parameter drift.
- [ ] 1.7 Add RED evidence and lifecycle tests for binary/gzip identity, byte and decision ceilings, per-access write-ahead seed journals, resource/checkpoint ordering, first-seed semantics, exact pre-start inventory reopening, dead-owner lease reclamation, one incomplete-chunk resume, ambiguous-output failure, missing external approval, mismatched approval digest, terminal failure, and independent verification.

## 2. Cross-Fitted Torch Runtime

- [ ] 2.1 Add the isolated Torch runtime with the unchanged state-conditioned ranker, model seed, hierarchical sampling, formal reward, Adam, entropy, discount, and gradient-ceiling controls.
- [ ] 2.2 Capture complete per-decision pre-action state tensors, policy terms, family diagnostics, rewards, and trajectory identity without adding baseline leakage or changing candidate selection.
- [ ] 2.3 Implement the registered 128-dimensional folded state features, canonical sparse representation, four deterministic per-chunk folds, trajectory-balanced ridge sufficient statistics, float64 Cholesky solve, and held-out predictions.
- [ ] 2.4 Build checked-in advantage records for every decision and reject incomplete fit coverage, fold leakage, invalid return/prediction/scale arithmetic, and any undeclared normalization before loss construction.
- [ ] 2.5 Build the exact five scalar components, invoke the shared-gradient ledger, register the ledger clip path as a second numeric intervention, compare the consumed Torch clip path, install the validated clipped complete gradient, and perform one Adam update only after all pre-step evidence checks pass.
- [ ] 2.6 Call the consumed public return-normalization and loss builders for the same-batch legacy-objective diagnostic without stepping it, and retain raw comparison metrics with no legacy-trajectory or outcome claim.
- [ ] 2.7 Retain ordered pre/post parameters and Adam step/moments and implement fixed-tolerance independent Adam transition replay without using optimizer state as component attribution.

## 3. Evidence, Control Plane, And Verifier

- [ ] 3.1 Implement canonical JSON and deterministic gzip little-endian codecs for sparse features, baseline models, five component gradients, complete and legacy-objective gradients, both clipping paths, raw installed gradients, and pre/post model and Adam states with uncompressed/stored hashes and bounds.
- [ ] 3.2 Add the standard-library control plane for contract inspection, source/runtime/native bindings, fresh inventory and registration schemas, read-only exact request, external-approval binding, exact authorization, output lease, append-only access journal, monotonic resources, bootstrap, checkpoints, terminal publication, and CLI routing.
- [ ] 3.3 Implement the fixed eight-chunk schedule, `32,768` decision ceiling, `576` access ceiling, `14,400`-second ceiling, exact four-chunk family-saturation stop, and no-evaluation-cohort rejection.
- [ ] 3.4 Implement one same-identity incomplete-chunk infrastructure resume with exact model, optimizer, Python RNG, Torch generator, chunk, seed, resource, and artifact restoration; reject a second resume and every evidence-driven retry.
- [ ] 3.5 Add the independent standard-library verifier with separate implementations of source/authority/approval checks, fold and fit reconstruction, ridge residual and prediction checks, advantage and scalar-loss arithmetic, binary vector reconstruction, both clipping paths, legacy-objective metrics, Adam transition replay, access-journal/resource accounting, checkpoint inventory, isolation, and terminal verdict classification.
- [ ] 3.6 Render deterministic source-only contract evidence and prove byte-identical output across two fresh processes without native loading, environment construction, empirical seeds, fitting, or policy training.

## 4. Source Verification And Publication

- [ ] 4.1 Run focused successor tests with a fresh system-temp pytest child, then run the directly dependent policy-input, ranker, hierarchy, formal-reward, simulator-adapter, and advantage-attribution suites.
- [ ] 4.2 Run import-isolation probes and strict validation for this change and the global OpenSpec set; preserve no new repository pytest-temp roots.
- [ ] 4.3 Run an independent code/spec/authority review, add RED regressions for every accepted finding, and make only narrow source fixes before registration.
- [ ] 4.4 Invoke the repository `commit` test gate exactly once at the source commit boundary, record correctness and duration against the existing feedback target, and do not rerun solely because it exceeds five minutes.
- [ ] 4.5 Update the implementation task state and project direction, then commit and push the clean source-only implementation without a cohort, native load, seed access, fitting, or training.

## 5. Fresh Registration Boundary

- [ ] 5.1 From the clean pushed implementation commit, generate a standard-library historical seed exclusion inventory that includes every consumed, reserved, diagnostic, canary, holdout, and previously untouched holdout identity.
- [ ] 5.2 Materialize exactly 512 fresh ascending training seeds, eight immutable chunks and folds, exact native/source/output identities, all resource and artifact ceilings, and every downstream authority as false in a new registration.
- [ ] 5.3 Independently verify the inventory and registration from a fresh process, run focused registration tests and strict OpenSpec validation, then commit and push this boundary without native loading or seed access.

## 6. Exact Human Authorization And One Mechanism Execution

- [ ] 6.1 Render and independently review one read-only exact execution request bound to the pushed registration, explicitly listing the native load, 512 scheduled seeds, cross-fitted fitting, eight possible updates, one resume reserve, CPU/time limits, output root, and false downstream authorities; do not publish authorization or execute.
- [ ] 6.2 Stop until a separate human message explicitly approves that exact request digest and bounds; reject broad standing permission, proposal approval, agent review, or approval of a different request.
- [ ] 6.3 After exact external approval, publish and independently verify the tracked authorization binding the canonical request and verbatim approval provenance.
- [ ] 6.4 Run all source-only preflight checks and start at most one evidence-bearing logical identity; stop on pre-start failure unless the unchanged identity satisfies the registered pre-start retry rule.
- [ ] 6.5 While the process is alive, monitor liveness only; do not inspect or mutate the active output root, change controls, replace seeds, tune, or launch Slay the Spire or CommunicationMod.
- [ ] 6.6 If one infrastructure interruption qualifies, resume only the same identity and incomplete chunk within the access/time reserve; otherwise preserve the terminal failure without retry.

## 7. Terminal Closeout

- [ ] 7.1 After process exit, run the independent verifier over the closed terminal bundle and reconcile exact chunks, folds, baselines, advantages, gradients, checkpoints, resources, isolation, artifacts, and verdict.
- [ ] 7.2 Publish a read-only postmortem that distinguishes valid completion, valid family saturation, pre-start blocking, and post-start failure and makes no policy-quality, formal-RL, loading, gameplay, qualification, or promotion claim.
- [ ] 7.3 Run focused terminal tests and strict OpenSpec validation, update project direction, sync the delta spec, archive the completed change, commit, and push the closeout.
- [ ] 7.4 Decide the next step only in a separate read-only audit of the terminal mechanism evidence; require a new proposal before any full policy-quality experiment or formal non-combat RL training.
