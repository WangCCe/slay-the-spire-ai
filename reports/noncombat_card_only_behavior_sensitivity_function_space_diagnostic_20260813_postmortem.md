# Card-only behavior sensitivity function-space postmortem

## Scope

This source-only diagnostic compared the r1 entry checkpoint (`004`) with every
complete checkpoint through `020` on the fixed 175-row validation probe. It did
not load native code, construct an environment, access seeds, train, evaluate a
fresh cohort, or authorize gameplay or promotion.

## Findings

1. The continuation changed parameters materially but did not change the final
   greedy policy on the fixed probe. Global parameter L2 movement was
   `1.496854485`; final exact-action and family flips were both zero.
2. The policy function did move. Mean joint symmetric KL was `0.003256890`, mean
   joint total variation was `0.011298590`, and the maximum row total variation
   was `0.165415848`. Only four final rows had a two-stage greedy margin at or
   below `0.50`; the median margin remained `4.672797680`.
3. Parameter updates did not oscillate. The mean cosine between consecutive
   update vectors was `0.927564399`, none were negative, and total path length
   was only `1.187248102` times the net displacement.
4. Function movement peaked and then receded while parameter updates continued
   in nearly the same direction. Mean joint KL from entry peaked at checkpoint
   `010` (`0.007292240`) and ended at `0.003256890` at checkpoint `020`.
5. Most parameter movement accumulated in hidden weights. Conditional hidden
   weight L2 movement was `1.189160544`, versus `0.026363043` in its scorer
   weight. Family hidden weight movement was `0.908471486`, versus `0.011776339`
   in its scorer weight.
6. Movement was not consistently toward Bottled labels. Bottled target joint
   probability improved on `88/175` rows; mean target joint log-probability
   delta was only `0.009527354`.

## Combined interpretation

The evidence rejects simple update cancellation and does not support blindly
extending the same schedule. It also does not justify a learning-rate increase:
Adam already moved parameters coherently, while the observable function response
was non-monotonic and remained far from most greedy boundaries.

The earlier r7 advantage diagnostic supplies one concrete mechanism candidate.
On its first consumed cohort, `133/566` card baseline predictions were clipped,
the advantage mean was positive (`0.037787002`), and total gradient norms were
small enough that the global `1.0` gradient ceiling was not the active limiter
(`0.007101663` conditional and `0.013333692` family before aggregation). The r1
runner did not persist per-step advantage or clipping telemetry, so this cannot
be established retrospectively across all 16 continuation chunks.

## Next experiment

Run a one-step baseline-clipping ablation from exact checkpoint `004`:

- collect one candidate-only 64-seed consumed-development cohort once;
- apply the current clipped cross-fitted residual update to branch A;
- recompute policy terms on the same stored trajectory data and apply an
  otherwise identical update using the unclipped held-out predictions to branch B;
- persist advantage summaries, objective components, gradient norms, update
  cosine, parameter movement, fixed-probe KL/margins, and model hashes;
- require branch A to reproduce the existing checkpoint `005` model exactly;
- stop after the single optimizer step with no fresh evaluation, policy loading,
  or promotion authority.

This experiment isolates whether lower-bound clipping materially changes the
training direction with 64 environment accesses. A longer ablation is justified
only if the one-step direction/function difference is material and all ownership,
support, reproduction, and isolation checks pass.

## Evidence

- `reports/noncombat_card_only_behavior_sensitivity_function_space_diagnostic_20260813/report.json`
  (`f096d230812d364a863407df61331601f0c8a6e97e868d8d157cd4eb58703d6f`)
- `reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1/report.json`
- `reports/noncombat_card_only_advantage_diagnostic_20260813_r1.json`
