# Non-Combat State/Action Teacher Sufficiency Audit Failure

## Result

The one registered execution is blocked. The runner reported
`audit exceeded the registered wall-time bound` after 293.7 seconds of total
command time and before canonical publication. The registered audit-body limit
was 120 seconds. The canonical output root is absent, so there is no partial
manifest, metric set, teacher verdict, or adapter-repair authority to consume.

The registration remains immutable at commit `40c936748`; its file SHA-256 is
`f33cf96301f9042611d17fcf49ebafde596f85e4f054d3a2f09d01965c32f498`.
The implementation commit is `18edd1400`, the external simulator commit is
`7476a819`, and all five audited external files remained clean and hash-equal.

## What Is Known

The pre-result static source trace is still valid evidence about SimpleAgent:

- route uses fixed act-specific room weights and caches one complete `mapPath`
  at map entry; the route decision block does not read current HP or gold;
- card reward reads offered card identity/upgrade and static tables, but its
  `deckCounts` loop iterates `lastCardReward`, not `gc.deck`;
- card equality remaps by `id`, `misc`, and `upgraded`; unlisted cards retain
  default priority zero, one priority entry is duplicated, and skip action bits
  are mapped by the adapter to either skip or Singing Bowl.

These facts show that SimpleAgent is a narrow heuristic and justify auditing its
fitness as a policy-quality teacher. They do not establish the registered
corpus-wide reconstruction rate, raw-adapter conflict count, projection alias
count, or terminal teacher-suitability verdict because those canonical outputs
were not published.

## Failure Boundary

This is a resource-contract failure, not a negative representation or teacher
result. The same registration must not be rerun, its 120-second limit must not
be edited, and no metric may be reconstructed from process timing. Model
fitting, native execution, new simulator evidence, gameplay, formal RL,
qualification, and policy promotion remain unauthorized.

The likely runtime costs are visible in code but were not tuned after the
attempt: the CLI validates and decodes the 191 MB train payload more than once,
the audit revalidates/canonicalizes it again inside its timed body, raw adapter
views are reserialized per candidate despite bound policy-view hashes, and
structured global/map features are rebuilt per candidate. These are hypotheses
for a separate performance change, not explanations proven by a post-result
profile.

## Required Follow-Up

Any recovery requires a separate OpenSpec change and fresh registration. It
must preserve the same corpus, source interpretation, four signature
definitions, suitability checks, verdict order, and 120-second audit-body
limit. It may only remove redundant validation/serialization and cache exact
pure computations, with synthetic equivalence regressions and a non-corpus
performance fixture before the new one-shot execution.
