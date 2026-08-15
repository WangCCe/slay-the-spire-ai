# Combat RL checkpoint soup zero-epsilon gate

## Decision

**FAIL: do not promote or continue training from the checkpoint soup.** The candidate tied the baseline on paired floor wins and finished six total floors behind it, so it failed two conditions in the preregistered conjunctive gate.

The result is close to neutral rather than a large regression. Weight averaging removed the more pronounced replicate-specific tails seen in R2 and R3, but it did not produce evidence of live improvement.

## Result

| Metric | R1/R2/R3 mean | Entry baseline | Gate condition |
| --- | ---: | ---: | --- |
| Paired floor wins | 4 | 4 | **FAIL** |
| Ties | 12 | 12 | Informational |
| Total floors | 399 | 405 | **FAIL** |
| Mean floor | 19.95 | 20.25 | Informational |
| Median floor | 16.0 | 16.0 | Informational |
| Act 2 entries | 9 | 8 | PASS |
| Act 2 boss reaches | 3 | 3 | PASS |
| Act 3 entries | 0 | 0 | Informational |
| Victories | 0 | 0 | PASS |
| Integrity warnings | 0 | 0 | PASS |

The paired mean floor delta was `-0.3`. Among eight non-tied seeds, each arm won four; the two-sided exact sign-test p-value is `1.0`. The candidate's largest gain and loss were both 17 floors.

## Interpretation

The replay diagnosis was directionally correct but insufficient for promotion: the soup reduced TD loss on all three retained panels and averaged away some replicate-specific noise, while fresh live outcomes remained indistinguishable from entry. More checkpoint selection on the same training recipe is unlikely to be the highest-value next step.

The next experiment should change the behavior distribution that creates replay. At the observed post-training epsilon near `0.84`, the current `0.30` expert mix implies approximately 30% expert actions, 59% random actions, and 11% network-greedy actions after warmup. A single bounded replicate with `expert_mix_prob=0.70` would reduce random actions to about 25% without removing exploration, while leaving the optimizer, reward, architecture, and training horizon unchanged.

## Integrity

- Both arms completed exactly 20 games in the preregistered seed order.
- All 20 `seed_played` values matched between candidate and baseline.
- Both arms logged exactly one `Max games reached (20)` exit.
- No replay rejection, episode-close failure, checkpoint-save failure, RL failure, or NaN was observed.
- CommunicationMod error-log growth contained only the wrapper command and dependency-load messages: 653 bytes for candidate and 662 bytes for baseline.
- CommunicationMod configuration was restored to SHA-256 `b42093ae...03c1`, and no related Python or game process remained after the gate.

## Next step

Stop unchanged schema-2 replications and checkpoint-selection variants. Run one fresh 25-game schema-2 training replicate from the exact frozen entry checkpoint with `expert_mix_prob=0.70`; keep every other training setting fixed. Diagnose the resulting replay and checkpoint before deciding whether it receives a live matched gate.
