# Card Counterfactual Corpus Expansion Result

The registered collection completed in 6,880.532 charged seconds with 2,509
native action branches. It published 497 complete train states and 126 complete
development states, above the fixed floors of 440 and 110. The reserved audit
range `80320..80383` was not accessed, no model was fit, and production
isolation remained unchanged.

Train contained 358 informative states (72.0%) and development contained 91
(72.2%). Mean return spread was 0.1653 in train and 0.1764 in development.
Train covered 78 take-card ids and development covered 74; `IMMOLATE` was the
only development card absent from train. Eight train seeds were censored by the
registered Courier restock blocker, below the limit of 16, while development
had no censors.

The train branch counter includes 17 attempted branches from subsequently
censored incomplete states. Those states are absent from the canonical corpus,
so its 497 complete rows contain exactly 1,988 candidate actions. This is the
intended fail-closed accounting behavior.

Verdict: the corpus is ready only for a separate source-only training proposal.
It does not establish policy quality and does not authorize audit access,
fresh evaluation, gameplay, or promotion.
