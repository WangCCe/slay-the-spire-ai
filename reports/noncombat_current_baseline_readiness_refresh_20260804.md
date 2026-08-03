# Current Baseline And Formal-RL Readiness Refresh

Date: 2026-08-04

## Verdict

Formal non-combat RL remains `not_ready_for_bounded_training_proposal`.
Bounded-training proposal consideration remains false.

The new Current baseline study does not change either blocked domain:

| Domain | Status | Current interpretation |
| --- | --- | --- |
| State/action | Passed | Unchanged from the strict formal-readiness r2 audit. |
| Reference isolation | Passed | Current, Bottled, and SimpleAgent remain auxiliary references, not reward or truth. |
| Reward | Passed | Terminal victory remains primary and reference labels remain excluded. |
| Baseline policy | Blocked | The one-shot Current study is `study_blocked`; no complete canary or floor exists. |
| Outcome support | Blocked | Evidence remains source-incomparable with zero target-supported victories and plug-in pass probability 0. |
| Evaluation | Passed | Registered cohort isolation and no-training boundaries remain intact. |

## Baseline Interpretation

The study retained 18 replay-identical rows for canary seeds `11000..11008`,
then terminated on `card_metadata_cost_invalid` for `Injury`. Its registered
canary required 32 rows for seeds `11000..11015`. Therefore:

- Current structural closure is not demonstrated.
- A credible Current baseline floor is not demonstrated.
- The partial Current mean floor `132/9` and paired difference `38/9` are
  descriptive only and cannot satisfy a gate.
- Bootstrap remained `not_run` and holdout seeds `12000..12063` were untouched.
- No same-question retry, replacement cohort, threshold change, or partial-row
  reinterpretation is authorized.

## Outcome Support

The baseline study is simulator-only and supplies no source-comparable live
target-supported outcome. The prior formal-readiness facts therefore remain
unchanged: target-supported victories are zero, source comparability is false,
and plug-in pass probability is `0.000000000000`.

## Next Direction

This change closes as a valid terminal blocked result. It must not launch
training, gameplay, a replacement baseline study, or a policy change.

The narrowest separately reviewable maintenance candidate is an offline audit
of card metadata cost-domain compatibility, beginning with empty-cost
unplayable Curse/Status entries such as `Injury`. Such an audit may improve the
bridge for future work, but it cannot reopen this study or establish a baseline
floor. Any new empirical baseline strategy requires a new project-level
decision and a distinct OpenSpec rationale, not a retry label.

## Evidence

The canonical JSON companion binds the terminal study manifest, journal,
metrics, rows, and the prior formal-readiness r2 report and matrix by path,
SHA-256, and byte size. All authority remains false.
