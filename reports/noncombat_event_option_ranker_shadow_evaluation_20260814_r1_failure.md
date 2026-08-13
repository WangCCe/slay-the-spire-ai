# Event Option Ranker Shadow R1 Preterminal Failure

## Status

No policy verdict was produced. Seeds `94300..94363` are consumed and MUST NOT
be reused for this model.

## Failure

The fixed run stopped after 807.7 seconds while evaluating an event branch whose
frozen Current continuation reached a shop. The simulator exposed six legal
card purchases plus leave; Current selected a visible shop inventory action that
had no legal simulator candidate, producing `shop + candidate_mapping_absent`.
No output report directory was published.

This is an incomplete-support boundary, not evidence for or against the event
ranker's policy quality. The replacement run retains the exact model, selected
threshold, resource limits, and evaluation gates, registers only this precise
shop continuation blocker as a censor, and uses fresh seeds `94400..94463`.
