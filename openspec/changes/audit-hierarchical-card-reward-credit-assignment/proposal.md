## Why

The consumed hierarchical simulator-learning experiment stopped after eight
training chunks because every card-reward decision in the final four-chunk
window had `take` as its unique raw-score maximum family, even though family
entropy remained close to `ln(2)` and stochastic `take`/`skip` selections stayed
near balanced. Before changing reward, advantage estimation, entropy, model
architecture, or another empirical cohort, the repository needs a deterministic
read-only account of the recorded family-level objective pressure and its
trajectory confounding.

## What Changes

- Add one standard-library-only audit that binds the exact verified terminal
  manifest, training rows, checkpoints, registration, postmortem, and source
  identity without importing Torch or native code.
- Reconstruct the registered reward-to-go and float32-normalized return for
  every training decision, then independently reconstruct direct family-logit
  policy, family-entropy, and expected-conditional-entropy pressure from
  recorded probabilities, selected families, and the two fixed `0.01`
  coefficients.
- Publish fixed chunk, pre-decision-floor, decision-timing, propensity-overlap,
  and family-margin strata for multi-family card rewards. Report raw counts and
  associations at decision and seed-cluster levels without treating repeated
  within-run rows as independent outcomes.
- Classify whether direct recorded family pressure is consistently aligned with
  the widening greedy `take` margin, reverses under the registered descriptive
  strata, or remains insufficient to isolate a mechanism. The classification
  is descriptive and cannot authorize a causal or OPE claim.
- Add canonical report and input-manifest artifacts plus mutation, order,
  arithmetic, determinism, import-isolation, and all-false-authority tests.
- Update project direction from the audited result. A later algorithm proposal
  remains separately reviewed and cannot reuse this audit as execution
  authorization.

Success means a fresh source-only process reproduces exact input bindings,
registered objective arithmetic, fixed strata, and the same bounded verdict.
It does not require the evidence to support a new experiment.

## Capabilities

### New Capabilities

- `noncombat-hierarchical-card-reward-credit-assignment-audit`: Defines the
  immutable existing-artifact inputs, exact descriptive family-pressure
  reconstruction, fixed confounding strata, bounded verdicts, canonical
  publication, and no-authority boundary.

### Modified Capabilities

None.

## Impact

The change is additive under `analysis_scripts/`, `tests/`, `reports/`, this
OpenSpec change, and `docs/project_direction.md`. It reads only the terminal
directory for
`noncombat-hierarchical-simulator-learning-20260806-r1` and its tracked
postmortem. It does not edit the consumed runner, verifier, registration,
authorization, checkpoints, model, training rows, agent, `main.py`,
CommunicationMod configuration, production checkpoints, or game files.

The audit creates no environment, accesses no new or replayed seed, loads no
native module or model, imports no Torch, fits nothing, and makes no policy
quality, target-supported-outcome, OPE, causal, formal-RL, gameplay,
qualification, loading, or promotion claim. Before the implementation commit,
rollback deletes only new uncommitted audit files; after that pushed commit but
before canonical publication, rollback requires an explicit revert or
superseding commit. After canonical publication, the report is immutable
historical evidence; correction requires a separately identified audit revision
rather than changing consumed inputs or rerunning the experiment.
