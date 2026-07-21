## Why

The fresh Ironclad A0 route comparison found that conservative routing reached an average floor of 24.2 and three Act 2 bosses but took no elites, while aggressive routing averaged floor 18.9, reached no Act 2 bosses, and died to elites in five of ten runs. A third, state-dependent baseline is needed to obtain bounded elite rewards without repeating the aggressive cohort's survival loss.

## What Changes

- Add an explicit Ironclad-only `adaptive` elite-route mode that evaluates current survivability, deck readiness, usable combat resources, prior elite exposure, recovery access, and downstream forced risk before accepting an optional elite. Other characters fail closed to the existing conservative route with a stable reason.
- Keep the first planner deliberately small: generate the existing conservative and aggressive candidate routes, inspect their complete path features, and select the aggressive candidate only when conservative contains zero elites, aggressive contains exactly one, and that optional elite passes every hard gate.
- Keep `conservative` and `aggressive` behavior unchanged and keep conservative as the live rollback mode until adaptive passes a fresh bounded promotion gate.
- Make adaptive decisions deterministic, explainable in logs, and independently testable through a pure risk assessment and route-selection contract.
- Re-evaluate adaptive risk after each map room so card, relic, potion, HP, act, and path changes can affect the next choice.
- Qualify the mode with no-training Ironclad A0 cohorts and preserve run files, debug/error logs, decision traces, and sim-divergence traces as evidence.
- Require at least three elite encounters, no more than two elite-caused death runs, an elite-death-run-to-elite-encounter ratio no greater than 25 percent, and no regression below the conservative cohort's average floor or Act 2 boss reaches before recommending a larger validation.
- Keep the first Ironclad `victory=true` run as the outer gameplay objective rather than treating route-gate passage as completion.
- Do not add RL training, tune combat policy, change shop/event/card-reward policy, import Bottled AI runtime code, or change the default/live route mode in this change.

## Capabilities

### New Capabilities

- `adaptive-elite-routing`: Deterministic state-aware elite risk assessment, bounded path selection, observability, rollback, and live promotion evidence.

### Modified Capabilities

None.

## Impact

- CLI construction and agent initialization in `main.py` will accept the new explicit mode.
- Map risk assessment in `spirecomm/ai/heuristics/map_routing.py` and route selection/replanning in `spirecomm/ai/agent.py` will gain adaptive-only behavior while retaining the existing route generator for both legacy candidates.
- Focused routing tests will cover risk gates, route constraints, replanning, logging, and legacy compatibility.
- A dated live-evaluation report will compare adaptive against the preserved 2026-07-20 conservative/aggressive baselines.
- No external dependency, checkpoint mutation, Communication Mod protocol change, or formal training authorization is introduced.
