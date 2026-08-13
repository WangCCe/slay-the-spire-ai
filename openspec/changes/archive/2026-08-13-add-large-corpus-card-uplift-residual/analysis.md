# Large-Corpus Card Uplift Residual Result

The fixed source-only study selected `shrinkage=1, strength=128` using five
train-only seed folds. The full-train model has 79 scalar parameters and was
persisted before development parsing. Reserved audit seeds, native code,
environments, gameplay, and CommunicationMod were not accessed.

Train cross-fit mean regret decreased from 0.08094 to 0.06767, maximum regret
decreased from 2.17544 to 2.01754, weighted pairwise accuracy increased from
0.50976 to 0.60644, and unique-best accuracy increased from 0.315 to 0.400.

On 126 development states, mean regret decreased from 0.09969 to 0.08104,
maximum regret remained 2.31579, weighted pairwise accuracy increased from
0.48333 to 0.58386, and unique-best accuracy increased from 0.29412 to 0.45098.
There were 29 action flips, 11 corrections, and one worsened action. The one
unseen take action used the frozen train-only global prior.

All fixed gates passed. The verdict authorizes only a separate collection and
evaluation of the reserved `80320..80383` audit cohort; it does not establish
policy quality or authorize production loading, gameplay, or promotion.
