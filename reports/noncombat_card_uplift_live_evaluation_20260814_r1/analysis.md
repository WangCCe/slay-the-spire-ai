# Card Uplift Live Evaluation R1

## Verdict

`card_uplift_live_evaluation_operational_pass_without_victory`

The runtime path passed: the frozen candidate completed all 10 registered games, emitted 95 decision rows with no row-level errors, stayed below 110 ms maximum measured decision latency, exited at the configured game limit, and restored the prior CommunicationMod configuration byte-for-byte.

The promotion gate did not pass. The cohort produced zero victories, reached a mean floor of 18.4 and a maximum floor of 33, and was not paired against a Current control cohort. It does not support a causal policy-quality claim.

## Outcomes

| Run | Floor | Result |
| --- | ---: | --- |
| 1786702921 | 7 | 3 Sentries |
| 1786702984 | 16 | The Guardian |
| 1786703083 | 16 | The Guardian |
| 1786703160 | 12 | Lots of Slimes |
| 1786703228 | 16 | Hexaghost |
| 1786703258 | 8 | Gremlin Nob |
| 1786703408 | 27 | 3 Cultists |
| 1786703479 | 16 | The Guardian |
| 1786703642 | 33 | Collector |
| 1786703776 | 33 | Automaton |

## Policy Diagnostic

Of 83 complete reward decisions, the candidate changed Current's action 62 times (74.7%). It selected skip 37 times versus Current's 4, including 34 take-to-skip substitutions. Another 27 substitutions changed one taken card to another. This is a broad policy replacement, not a narrow residual correction.

That intervention shape is the main actionable result. The frozen residual had positive fresh paired simulator floor evidence, but its live deployment is heavily biased toward rejecting cards and did not produce a victory in this cohort. More unpaired games with the same candidate would measure variance without addressing the observed distribution shift.

## Next Decision

Do not promote the candidate and do not immediately extend the same live cohort. Run a bounded training/calibration experiment that directly constrains excessive skip and overall intervention rates while preserving the existing source, model, and outcome lineage. Promotion remains gated on fresh simulator evidence followed by a new bounded live cohort.

This evaluation is observational and unpaired. It establishes operational viability and a training target, not causal harm or benefit relative to Current.
