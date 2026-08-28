## Context

Production r16 frequently proposes `EndTurn` with playable energy, after which
the outer `ENERGY_GUARD` selects and continues a deterministic card sequence.
The failed latent-gated candidate intervened before that guard and replaced its
trigger with a learned card action. Fresh replay agreement was only 31.9%, and
the candidate lost the live matched gate. A separate larger LightSTS RL
replication also regressed on victories, reward, and HP.

LightSTS already supplies deterministic environment cloning, RL-v2 state and
action mapping, the frozen r16 simulator shadow, a deployment guard proxy,
native reward calculation, and paired full-policy evaluation. The missing
evidence is an action-level return comparison against the action the guard
would actually execute.

## Goals / Non-Goals

**Goals:**

- Generate source-bound paired returns for the guard action and legal
  alternatives from identical supported simulator states.
- Learn only from positive advantage relative to the guarded baseline.
- Place the development residual conceptually after guard selection and
  abstain to the guard action by default.
- Use seed-disjoint corpus and policy holdouts with fixed gates and one recipe.
- Spend the majority of runtime on corpus generation, fitting, and paired
  simulator evaluation rather than broad repository tests.

**Non-Goals:**

- Reproduce production guard semantics exactly or claim mechanics equivalence.
- Start Slay the Spire or CommunicationMod.
- Change r16, live combat routing, production checkpoints, rewards, or action
  spaces.
- Tune horizon, advantage margin, architecture, threshold, seed, or optimizer
  budget after seeing the fixed POC result.
- Authorize gameplay, qualification, promotion, or a formal policy-quality
  claim.

## Decisions

### Sample only guard-intervention states

The corpus SHALL follow the frozen r16 guarded policy and retain states only
when the raw parent proposes `EndTurn`, the guard proxy selects a legal card,
and at least one distinct legal alternative exists. This directly targets the
failed deployment interaction and avoids relearning direct parent behavior.

Alternative considered: sample every combat state. Rejected because it
reintroduces direct-policy drift and spends most rollout budget outside the
observed failure class.

### Compare cloned branches under one continuation policy

For each retained state, clone one branch per eligible first action. Apply that
first action, then continue with the same deterministic frozen r16 guarded
policy for at most eight further decisions or until terminal. Sum the existing
native rewards with discount 0.99. Exclude the complete paired state if any
branch is unsupported or cannot settle within the bound.

Alternative considered: compare only immediate native reward. Rejected because
the guard already optimizes a one-step proxy and the live failures involved
multi-action sequences such as `Corruption` plus several `Defend` cards.

Alternative considered: full-combat rollout. Deferred because multiplying
every legal action by full terminal rollouts is too expensive for the first
mechanism POC.

### Define one fixed positive-advantage label

The guarded action is the zero-advantage baseline. The target action is the
eligible branch with maximum paired return, with deterministic RL action index
as the tie-breaker. A state is positive only when target advantage is at least
0.5 reward units. Duplicate card-slot actions with identical encoded identity,
features, and target SHALL be grouped as one behavior.

The corpus sufficiency gate requires both train and fresh evaluation partitions
to contain positive and negative states, at least 100 positive training states,
and at least three distinct positive target action identities. Failure stops
the change before model fitting.

### Train a post-guard abstaining residual

If the corpus passes, a small development-only head SHALL consume frozen parent
latent features, the guard action one-hot vector, and the legal action mask. A
gate predicts whether positive advantage exists; an action head predicts the
best alternative only on positive rows. The frozen parent and guard baseline
remain unchanged. The configured hard gate defaults to the guard action.

Alternative considered: reuse the pre-guard latent adapter. Rejected because
it cannot represent the actual guarded baseline and already failed live.

### Require fresh paired policy improvement

After a seed-disjoint classification holdout, evaluate the frozen residual and
the guarded baseline on identical fresh LightSTS profiles. The POC is promising
only if candidate-only victories are at least control-only victories, mean
reward and mean HP deltas are non-negative, no nonterminal exclusions occur,
and the residual actually intervenes. Otherwise close the recipe without a
sweep.

## Risks / Trade-offs

- [The LightSTS guard proxy is not production `ENERGY_GUARD`] -> Treat all
  results as simulator-only mechanism evidence and require later real-game
  divergence calibration before any live candidate.
- [Eight-step return can miss delayed consequences] -> Publish horizon and
  terminal coverage; do not reinterpret a no-go by changing the horizon in the
  same change.
- [Branch count can make corpus generation expensive] -> Bound seeds, retained
  states per profile, alternatives per state, and decisions per rollout.
- [Action ties can inflate apparent diversity] -> Canonicalize behavior-
  equivalent duplicate slots before labeling.
- [Positive labels may be sparse] -> Stop at the corpus sufficiency gate rather
  than weakening the advantage margin post hoc.
- [Residual may exploit simulator divergence] -> Keep artifact development-only
  and prohibit gameplay or production loading.

## Migration Plan

No production migration is required. Implement and run the POC in new offline
modules and report directories. Rollback removes those files and leaves r16,
CommunicationMod configuration, and gameplay state unchanged.

## Open Questions

No design question may be answered by tuning after the fixed POC. A future
change may revisit rollout horizon or production guard integration only after
this report is closed and independently reviewed.
