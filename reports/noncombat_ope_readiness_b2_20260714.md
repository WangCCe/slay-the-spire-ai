# Non-combat OPE readiness: B2 proof of concept

## Verdict

The offline accounting loop is reproducible, but candidate-policy OPE is not
ready. Both target audits reconstruct exactly 230 decisions in 25 independent
run trajectories. The behavior-identity self-check passes exactly. The
deterministic Current target retains only 8 nonzero-weight trajectories, has an
ESS of about 7.17, and concentrates about 22.73% of normalized weight in one
trajectory. All 25 terminal outcomes are losses.

No policy value, uplift, confidence interval, formal RL reward, training
authorization, or live-promotion claim is produced by this proof of concept.

## Frozen source

| Field | Value |
| --- | --- |
| canonical sample | `known_propensity_exploration_eval_20260714_b2_samples.jsonl` |
| sample SHA-256 | `b7436b5a7ef12f345e54172f56ecb05b7aefe59f4ed9007805cc20aa4e90820f` |
| sample policy commit | `99dd44a6bec3a8fea64af76ddcc8fa587b06e5fd` |
| run allowlist SHA-256 | `c1443104e56759ba2d48553346c69054b2eb8a12769830567779f286b1f96942` |
| B2 qualification SHA-256 | `dd64a5144b23c6083f2a0f24f1ca544ff966c12cecc2b4147b1dc99623641891` |
| OPE implementation commit | `94ae36c326bdbf16f1d3d8c65ed01570dd963d08` |

## Reconstructed support

| Metric | Behavior identity | Deterministic Current |
| --- | ---: | ---: |
| complete trajectories | 25 | 25 |
| confirmed decisions | 230 | 230 |
| nonzero-weight trajectories | 25 | 8 |
| zero-weight trajectories | 0 | 17 |
| exact ESS | 25 | `1936291079828224375201 / 270073503359154748801` |
| ESS display value | 25.0 | 7.1694966583 |
| ESS fraction | 1.0 | 0.2867798663 |
| maximum normalized weight | 0.04 | 0.2272556438 |
| victory classes represented | 1 | 1 |
| identity invariants | pass | not applicable |
| overlap screen | blocked | blocked |
| estimator validation | blocked | blocked |
| OPE / causal / training / promotion | blocked | blocked |

The identity target has exactly one ratio and one trajectory weight for every
logged run, so it proves grouping and arithmetic integrity. It does not prove
candidate overlap. The deterministic Current result is the relevant warning:
17 trajectories receive exact zero weight because at least one logged selected
action has zero probability under Current.

## Independent replay

`analysis_scripts.verify_noncombat_ope_artifacts` does not import the main OPE
readiness implementation. It reparses the canonical JSONL and independently
checks source hashes, target manifest hashes, exact support normalization,
decision ratios, trajectory products, ESS, concentration, outcome variation,
screen blockers, and closed downstream gates.

| Target | Checks | Result | Readiness JSON SHA-256 |
| --- | ---: | --- | --- |
| behavior identity | 21,918 | pass | `d582bbc14fe729f20c7b915934091a4a5357d82a84599d40f7598a7aa8a402fd` |
| deterministic Current | 21,684 | pass | `81b7410cf49b8b285711251a1d52f2a2902b4146ecc7c200c830f65340a1c747` |

Tamper regressions separately prove that changed target bytes and changed
reported decision ratios are rejected.

## Live isolation

The offline POC did not start Slay the Spire, Java, or Python gameplay/training
processes. Pre/post fingerprints were identical:

| Surface | Count | Fingerprint |
| --- | ---: | --- |
| CommunicationMod config | 1 | `f1bc7000795e225d08393490ddd53ed523a15ad2903c5b0b464b0b20af4e2ed1` |
| checkpoints | 208 | `65b31a1a0b7de8eaebd63bc2bf382fa18d29f0b8ad0f50e026cfacfae83f366b` |
| run records | 1,060 | `4bac8d9d77bc4afde2005694cee6d71d055193669f33c8656a14d14be2b5edcf` |

## Verification

| Check | Result |
| --- | --- |
| focused OPE, verifier, and evidence tests | 94 passed in 4.94s |
| full Windows pytest suite | 2,572 passed in 97.45s |
| OpenSpec strict validation | 34 passed, 0 failed |
| independent artifact replay | 43,602 checks passed |
| target-byte and ratio tamper regressions | passed |
| completion code review | 5 important findings resolved; re-review clean |
| Git whitespace check | passed |
| live gameplay/training process check | 0 matching processes |

## Remaining blockers

- There are 25 complete trajectories, below the 100-trajectory screen.
- Current has 8 nonzero-weight trajectories, below the 50-trajectory screen.
- Current ESS, ESS fraction, and maximum normalized weight all fail their
  minimum overlap screens.
- B2 contains no victory, so the primary terminal outcome is degenerate.
- No estimator, uncertainty method, confidence interval, or estimator
  validation gate has been specified.
- Terminal victory and floor progress remain separate diagnostics and are not a
  formal non-combat RL reward.

## Next gate

Do not start formal non-combat RL training from B2. The next bounded stage is to
collect additional fresh known-propensity trajectories until both outcome
classes and candidate-policy support improve, then propose a separate
estimator-validation change. That change must pre-specify the estimator,
uncertainty method, trajectory-level split/evaluation protocol, synthetic and
identity calibration tests, and policy-comparison acceptance criteria. Passing
the current overlap screens alone must still not authorize OPE or promotion.
