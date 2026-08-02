# Current Policy Simulator Bridge POC

Verdict: `frozen_bridge_not_compatible`.

This is structural bridge evidence only. It does not establish policy quality, a baseline floor, reward validity, outcome support, promotion, or formal RL readiness.

## Frozen Rows

| Category | Seed | Decision | Status | Result |
| --- | ---: | ---: | --- | --- |
| `route` | 4000 | 0 | `passed` | `route:map_node:0:0` |
| `card_reward` | 4000 | 1 | `passed` | `card_reward:take:0:0:armaments` |
| `shop` | 4000 | 5 | `passed` | `shop:remove_card` |
| `event` | 4000 | 11 | `failed` | `missing_event_option_semantics` |

## Stage 2

Stage 2 was not run because at least one frozen structural gate failed.

## Authority

- `baseline_floor_authorized`: `false`
- `formal_rl_readiness_authorized`: `false`
- `fresh_evidence_authorized`: `false`
- `gameplay_authorized`: `false`
- `promotion_authorized`: `false`
- `reward_authorized`: `false`
- `training_authorized`: `false`

A separate OpenSpec change and untouched preregistered seeds are required before any baseline-floor study.
