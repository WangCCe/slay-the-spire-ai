# Parent-to-weight-one interpolation diagnosis

## Selection

Construct a weights-only checkpoint at `alpha=0.20` from the promoted parent toward the rejected weight-one successor. This is an exploratory candidate with no promotion authority until it passes a fresh matched gameplay gate.

## Replay evidence

The interpolation grid was evaluated on the promoted-parent, weight-0.5 successor, and weight-1.0 successor replay buffers, each containing 4,096 transitions.

| Alpha | Minimum parent agreement | Mean parent agreement | Mean normalized SmoothL1 | Worst normalized SmoothL1 |
|---:|---:|---:|---:|---:|
| 0.10 | 95.97% | 96.39% | 0.9808 | 0.9843 |
| 0.20 | 93.38% | 94.01% | 0.9624 | 0.9696 |
| 0.30 | 91.31% | 92.17% | 0.9459 | 0.9574 |
| 1.00 | 85.33% | 86.99% | 0.8951 | 0.9611 |

`alpha=0.20` is the largest tested interpolation that keeps the minimum panel agreement at or above 93% while improving SmoothL1 on every panel. This rule is exploratory and was chosen after observing the rejected full-candidate gate, so only a new fresh gameplay cohort can qualify the checkpoint.

## Artifact

The checkpoint contains only the interpolated online network and metadata; it inherits no optimizer, replay, target-network, epsilon, or episode state. It round-tripped exactly, all tensors are finite, and `RLAgentV2` loaded it successfully in CPU evaluation mode.
