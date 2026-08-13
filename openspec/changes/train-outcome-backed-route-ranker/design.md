## Context

The exact API v3 simulator already exposes legal route candidates, cloneable environments, and the formal floor-progress/victory return. The current route residual POC instead fits SimpleAgent labels, while the later teacher audit shows that teacher does not read current HP, gold, or other run resources. The useful next experiment is therefore direct route action credit, not another imitation model.

## Goals / Non-Goals

**Goals:**

- Collect complete per-source returns for every legal route action on fixed train and development seed cohorts.
- Train one deterministic CPU ranker with train-only checkpoint selection.
- Evaluate exactly once on development rows against both the frozen initialization and the Current optimized route action.
- Finish in one implementation/experiment cycle with compact, replayable artifacts.

**Non-Goals:**

- No card, shop, event, combat, live game, CommunicationMod, production checkpoint, formal RL, OPE, or promotion work.
- No reserved card seed access and no same-development-cohort hyperparameter tuning after the result.
- No claim that native SimpleAgent continuation is an unbiased estimate of live Current-policy value.

## Decisions

1. **Generalize the existing branch evaluator by expected source category.** The card wrapper remains unchanged, while a category-aware entry point accepts `route`. This reuses clone, transition, reward, terminal, and source-immutability checks instead of copying them.

2. **Use fixed fresh cohorts `93000..93127` for train and `93128..93159` for development.** Each route source is evaluated only when it has multiple legal actions. Every candidate branch uses a fresh frozen Current-policy session to re-decide from each subsequent state and continues to terminal under the existing formal reward. The root source-sampling trajectory still follows native continuation.

3. **Record Current optimized policy as the decision baseline.** A route-only `CurrentPolicyBridgeSession` evaluates the immutable source snapshot. The experiment stores its selected action alongside branch returns; it does not use Current labels for fitting.

4. **Use one state-conditioned ranker and one train-only selection split.** The existing 1024-wide state/candidate projection and 64-unit ranker are reused. Seeds divisible by four form the internal tune split; checkpoints are fixed at epochs 1, 2, 4, 8, and 16. The selected epoch is refit on all train rows before development is read.

5. **Keep the execution contract intentionally small.** One CLI writes configuration, sparse JSON datasets, model state, metrics, and report. Source/native/metadata hashes and seed ranges are recorded, but separate request, authorization, launch-manifest, and review publications are not required.

## Risks / Trade-offs

- **Current continuation couples route value to the frozen downstream policy** -> Report this explicitly and require a later fresh-policy evaluation before any runtime use.
- **Native baseline continuation rejects off-path route branches** -> Never call `step_native_baseline` after the forced route action; re-decide every branch transition with Current policy.
- **Some branches may hit unsupported simulator states** -> Censor the affected source and report reasons; fail if support drops below the fixed minimum.
- **A 64-unit model can overfit a modest corpus** -> Select epoch only on a train-internal split and require a one-shot disjoint development win over Current policy.
- **Current bridge metadata can drift** -> Verify the bound metadata file hash before collection and fail closed on bridge errors.
- **Long branch collection dominates runtime** -> Bound source states, branches, decisions, and wall time; do not run the full pytest suite in this experiment cycle.

## Migration Plan

Add the generalized evaluator, runner, and focused tests; run the fixed experiment once; publish its terminal report. Rollback deletes only these additions and the new report directory. Production gameplay and checkpoints remain untouched.

## Open Questions

None before the first bounded experiment. A positive result still needs a separate fresh simulator or live shadow evaluation before policy integration.
