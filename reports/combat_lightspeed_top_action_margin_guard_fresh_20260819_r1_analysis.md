# Fresh Top-Action Margin Guard Result

## Verdict

Retain production r16 and stop the parent-margin-guard objective family. No candidate qualifies for a larger confirmation, packaging, or gameplay.

## Fresh Evidence

The top-action run completed 83,464 replay transitions and 256 optimizer updates. Guard eligibility averaged `102.40` rows per batch, but ranking violations increased from 12 to 18.

On unused evaluation seeds, candidate-minus-r16 results were:

- Prior guarded control: reward `-0.433203`, HP `+0.023895`, victories `5:14`.
- Card-ranking guard: reward `-0.247618`, HP `+0.309438`, victories `7:13`.
- Top-action margin guard: reward `-0.407319`, HP `-0.062127`, victories `5:12`.

Production r16 led all four policies in reward and victories. The card-only candidate retained a modest HP signal, but not enough reward or wins to justify continuation.

## Implication

The problem is no longer well described as insufficient anchoring. Uniform non-EndTurn replay plus one-step TD learns a bare policy, while production executes a guarded composite policy. More margin penalties would tune around the symptom and further restrict RL without correcting that objective mismatch.

The next training work should make LightSTS collection or targets deployment-consistent, for example by collecting transitions under the same guard-aware executed policy and using complete multi-step outcomes. It should not tune these weights or caps on the observed cohorts.
