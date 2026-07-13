# Known-Propensity Exploration Dry Run - 2026-07-13

## Scope

- Source commit: `ff1d3fb48e7b9069055ff535e247380bc5b78849`
- Python: `D:\anaconda\envs\stsai\python.exe`
- Agent: `optimized`
- Category rates: `card_reward=0`, `shop=0`
- Per-run alternative budget: `0`
- Command: `main.py --agent optimized --max-games 1 --noncombat-exploration-dry-run`

## Result

- Process exit code: `0`
- Startup-to-exit time: about `2.2s`
- Manifest hash: `0fb00a7cf7ca34dcff6f92bf4600ae527c54c684807cca01a6f30261f8d1461a`
- Effective config hash: `4b1f8c37bce84558de2eb06253080c25bcbdaa09a7492083c1a36d2b55e6f245`
- Config file SHA-256: `afc7e53fe8b4bf45805b9e782d98b0e88656f90fb4846d614efdc2d98f5ce710`
- The process exited before Coordinator construction and agent/model loading.
- No exploration trace was created on the zero-rate dry-run path.

## Isolation

`CommunicationMod/config.properties` matched the pre-session snapshot after exit:

- SHA-256: `a90598500660dc99c85a59319bda4b6a3485b4927cec539520b6567002d3f148`
- Size: `505` bytes

No checkpoint appeared in the dry-run isolation manifest, and the process did not enter any checkpoint discovery, load, training, or save path.

## Boundary

This verifies explicit startup, provenance capture, default zero-rate behavior, isolation, and clean shutdown only. It is not nonzero exploration evidence and does not support OPE, causal uplift, formal non-combat RL training, or live policy promotion.
