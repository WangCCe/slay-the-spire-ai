# Combat RL Stratified Provenance Successor R1

## Result

The preregistered CPU recipe completed exactly 64 optimizer updates. Candidate
checkpoint `8d82e0ee5486daeb963d524a6e34b599716b966976f1406e4220973760df6ccf`
round-trips exactly and remains development-only.

The candidate is not eligible for a fresh holdout. It changed 38 of 106 direct
validation decisions (`35.85%`), above the fixed `10%` ceiling. Production r16
therefore remains authoritative and this replay will not be used for another
recipe or threshold adjustment.

## Gate Detail

All other fixed conditions passed:

- validation one-step TD loss improved from `3.41145` to `3.07758`;
- overall parent disagreement was `62.88%`, above the `5%` materiality floor;
- override executed-label agreement improved from `18.47%` to `47.44%`, an
  absolute uplift of `28.98` percentage points;
- positive-energy End Turn count fell from `199` to `18`;
- both validation provenance strata were nonempty;
- optimizer budget, objective finiteness, override sampling, and candidate
  serialization checks passed.

Reducing the update count from 256 to 64 did not isolate direct-policy behavior.
The next recipe line should change how direct parent behavior is protected, not
mechanically continue lowering steps on this corpus.

## Execution Note

An initial command bound to source `243150069` exited during module import under
Python isolated mode, before loading the checkpoint or creating an output
directory. Source `ef661a471` added a direct isolated-entrypoint regression and
produced the only fitted candidate. No optimizer budget was consumed by the
pre-start failure.

## Authority

This result grants no fresh holdout, gameplay, qualification, promotion, policy
quality, or production-checkpoint authority. It is evidence for ending this
recipe line and redesigning direct-policy protection on separately registered
data.
