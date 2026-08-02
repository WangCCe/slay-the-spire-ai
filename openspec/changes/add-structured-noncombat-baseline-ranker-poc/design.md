## Context

The baseline warm-start trained one shared `128`-unit MLP over a signed hash of
the recursively flattened state and candidate JSON. The completed failure audit
found `76.32%` train and `68.58%` validation agreement on rows with more than
one legal action, with early rollout divergence concentrated in route and card
reward. The current projection encodes deck and map entries by list index,
shares one scorer across all categories, and provides no explicit relationship
between a route candidate and its reachable suffix or between a card/shop item
and the current deck.

The preserved warm-start train dataset has 32 baseline-following seeds and all
four target categories. It is already observed evidence and may support model
selection only as an implementation-fit corpus. The observed validation seeds
and untouched final seeds cannot be used by this POC. No live evidence is
needed, and the external simulator must not be loaded.

## Goals / Non-Goals

**Goals:**

- Test one fixed structured representation against one legacy-representation
  control under seed-grouped, train-only cross-validation.
- Remove list-position dependence from deck, relic, potion, and map summaries;
  expose candidate-relative route and item/deck information available in the
  preserved schema.
- Train and evaluate on real choices while retaining singleton rows as a
  separately reported data-quality stratum.
- Produce a deterministic, hash-closed implementation-fit result that can
  justify or reject a later fresh-study proposal.

**Non-Goals:**

- No native simulator load, new seed, independent policy rollout, floor or
  victory claim, DAgger, reward optimization, formal RL, live gameplay, policy
  loading, qualification, or promotion.
- No use of the observed validation or untouched final cohorts for features,
  schedule, thresholds, fitting, selection, or reporting.
- No claim that SimpleAgent is optimal or permanent ground truth, and no
  Current/Bottled labels until their simulator bridges are validated.
- No open-ended architecture search or post-result retry under this change.

## Decisions

### 1. Derive one train-only canonical input before model execution

The POC preparation command will verify the preserved warm-start artifact and
its manifest, select only `datasets.train`, validate every demonstration row,
and write a smaller canonical train-only input that binds the source artifact
hash, train dataset hash, expected seeds, schema, and teacher policy. Model code
will accept only this derived input and reject validation/final cohort fields.

The source artifact may be the local canonical JSON or its committed
deterministic gzip archive. Decompression and extraction are mechanical and do
not expose non-train rows to feature or model selection. Copying rows by hand or
reading the failure-audit tables as model input is not allowed.

### 2. Compare exactly two fixed representations on the same real choices

The control is `legacy-hash-mlp-multichoice-v1`: the existing leakage-stripped
state-plus-candidate signed hash and one shared hidden-layer scorer, retrained
from its fixed seed using only rows with at least two legal candidates.

The candidate is `structured-category-ranker-v1`. It uses the same complete
candidate sets and bounded candidate-masked cross entropy, but encodes:

- global scalar state and normalized HP/gold/floor/act values;
- deck, relic, and potion multisets by stable identity and count, independent
  of source list order;
- route candidates by selected room, coordinate delta, reachable-node counts,
  and deterministic suffix path summaries computed from the reported map DAG;
- card-reward candidates by kind, stable card identity, upgrade state, deck
  duplicate counts, and skip/bowl context;
- shop candidates by kind, stable item identity, price, affordability,
  post-purchase gold, owned/deck counts, and removal context; and
- event candidates by stable event identity, option index, and normalized event
  data.

Structured categorical tokens use separate stable namespaces and a larger
fixed signed-hash space; numeric and interaction features use named stable
slots. Four category-specific hidden-layer heads prevent route frequency and
semantics from defining the card, event, or shop score. Candidate order and
irrelevant state collection order must not change scores. Action ids remain the
original adapter ids and no candidate may be filtered.

A category-specific structured scorer is preferred over a larger generic MLP
because the audit identified missing relationships, not merely low parameter
count. A graph neural network or transformer is deferred: 32 observed seeds do
not justify that complexity, and this POC should isolate whether explicit
structure is useful first.

### 3. Use deterministic seed-grouped cross-validation

Sort the 32 registered train seeds and assign them round-robin to four fixed
folds. For each model candidate and fold, train on the other 24 seeds and score
the held-out eight. A seed and all of its decisions therefore occur on only one
side of a fold. Both candidates use the same fixed CPU seed, epoch count,
optimizer schedule, category-balanced objective, and multi-candidate rows.

After all fold predictions are concatenated in canonical seed/decision order,
the evaluator reports row counts, singleton rates, exact agreement, cross
entropy, macro category agreement, per-category values, per-fold values, and
paired deltas. Singleton rows are checked for legality and coverage but cannot
enter loss, agreement, cross entropy, or the selection gate.

### 4. Freeze one implementation-fit selection gate before execution

The checked-in registration binds the source hashes, exact two candidates,
fold assignment, schedule, resource bounds, metrics, and thresholds before the
structured candidate is fit. Selection requires all structural and replay
checks, at least the registered positive overall and macro multi-candidate
agreement deltas over the control, non-regression on route and card reward, and
non-worse aggregate multi-candidate cross entropy. Missing category coverage,
non-finite values, or a threshold failure yields
`poc_valid_without_structured_candidate`; contract or resource failures yield
`blocked`.

If selected, one final implementation artifact may be fit on all 32 train seeds
using the already bound configuration. It remains an implementation artifact,
not a policy-quality result. There is no alternate candidate, fold scheme,
schedule, or retry in this change.

### 5. Reproduce and publish a no-authority artifact set

One bounded execution and one identical replay must reproduce the derived input
identity, fold assignments, model tensors, predictions, metrics, verdict,
report, and manifest. Timing is noncanonical. Canonical outputs are published
atomically under a dedicated report directory outside checkpoint discovery.

The manifest marks simulator rollout, new native evidence, live gameplay, live
loading, DAgger, formal RL, qualification, OPE reinterpretation, and promotion
authority false. A positive POC authorizes only drafting a separate fresh-study
preregistration with entirely new train, validation, and final cohorts.

## Risks / Trade-offs

- **Observed train data can overstate progress** -> Call the result
  implementation fit only; group by seed and require fresh preregistered
  evidence for every quality claim.
- **Feature engineering can encode SimpleAgent quirks** -> Preserve all legal
  actions, keep labels auxiliary, and avoid production loading or reward use.
- **Hash collisions remain possible** -> Use semantic canonicalization,
  separate namespaces, a larger fixed space, and publish token/bin collision
  diagnostics.
- **Route summaries may still omit strategic context** -> Report category and
  fold failures; do not add post-result route features under this change.
- **Rare event/shop choices can make fold metrics noisy** -> Publish counts and
  paired deltas, require aggregate category coverage, and avoid treating a
  single fold as policy evidence.
- **The source artifact is large** -> Derive and hash one train-only input once,
  enforce memory/time bounds, and keep raw warm-start artifacts immutable.

## Migration Plan

1. Implement pure train-input, feature, model, grouped-evaluation, verdict, and
   artifact contracts with synthetic fixtures.
2. Freeze the exact POC registration and derive the train-only input from the
   preserved warm-start artifact without loading a native module.
3. Run focused tests, compilation, the repository commit gate, and strict
   OpenSpec validation; commit and push before model execution.
4. Execute the registered POC once plus one deterministic replay, then perform
   a read-only leakage, metric, hash, authority, and inventory audit.
5. Publish the result, update project direction, sync/archive the change, and
   either draft a separate fresh-study proposal or stop at the negative result.

Rollback deletes only the new offline runner, tests, registration, reports, and
spec artifacts. It does not alter prior studies, checkpoints, live config,
production agent code, or the external simulator checkout.

## Open Questions

None for this POC. Static complexity/runtime constraints and synthetic tests
freeze the legacy control at a `1024`-wide hash with one `128`-unit shared head,
the structured candidate at a `2048`-wide hash with four `64`-unit category
heads, and both at 20 deterministic Adam epochs over four round-robin seed
folds. Selection requires at least `+0.03` overall and macro multi-candidate
agreement, no route or card-reward agreement regression, and non-worse mean
cross entropy. Each execution is limited to 1,500 rows, 32 candidates per row,
nine model fits, and 900 seconds.
