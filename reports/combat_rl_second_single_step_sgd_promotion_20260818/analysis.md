# Second single-step SGD combat promotion

## Decision

Promote the frozen second single-step SGD candidate as the production combat
baseline for bounded five-game evaluation launches.

This is a separate decision from the 20-pair matched live gate. The gate
restored the previous production configuration before qualification. Promotion
uses the complete replay and live evidence chain and does not interpret the
single favorable floor as a large live effect.

## Basis

- On fresh parent-policy replay r5, candidate SmoothL1 was `4.214702` versus
  `4.218847` for the parent, with `99.8898%` parent action agreement.
- On the later untouched r6 replay, candidate SmoothL1 was `4.138884` versus
  `4.143240`, with `99.9722%` parent action agreement.
- The matched live gate passed every registered condition: one candidate floor
  win, zero parent floor wins, nineteen ties, and `467` versus `466` total
  floors. Act progression was equal at 11 Act 2 entries and seven Act 2 boss
  reaches per arm.
- Both live arms completed without invalid actions, RL failures, agent-level
  fallbacks, training actions, tracebacks, critical errors, or post-start
  CommunicationMod error growth.

## Scope

The production command remains evaluation-only with epsilon zero, conservative
routing, and a five-game launch bound. It loads only the candidate weights and
does not load optimizer or replay state. The replaced r7 production config is
retained as a fixed rollback artifact.

Nineteen of twenty live pairs tied and neither arm won a run. This evidence
supports a conservative low-risk baseline replacement, not a material win-rate
claim or completion of the first-victory goal.

## Next iteration

Collect a fresh on-policy replay cohort under the promoted policy and reserve
it as untouched validation. The already consumed replay can then support a
bounded multi-update successor. This moves the next iteration toward actual
training while retaining one fresh replay and one matched live gate as the
promotion boundary.
