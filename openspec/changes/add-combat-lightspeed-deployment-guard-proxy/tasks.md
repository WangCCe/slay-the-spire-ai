## 1. Configuration And Regression Coverage

- [x] 1.1 Add the registered deployment guard proxy mode to smoke configuration, CLI validation, and report binding while preserving `none` as the default.
- [x] 1.2 Add focused regressions for default pass-through, eligibility boundaries, deterministic replacement, unsupported replacement fallback, and symmetric telemetry.

## 2. Evaluation Implementation

- [x] 2.1 Implement clone-based immediate-native-reward selection for eligible raw end-turn actions without changing collection, fitting, or checkpoint state.
- [x] 2.2 Integrate per-policy and aggregate guard proxy telemetry into paired held-out evaluation and bump the report schema.

## 3. Verification And Counterfactual Evidence

- [x] 3.1 Run focused pytest for the LightSTS smoke and OpenSpec validation; assess the existing full-suite gate and run another full gate only if the focused evidence reveals broader impact.
- [ ] 3.2 Rerun the frozen guarded-control experiment with the proxy, verify unchanged candidate parameter identity, and publish a bounded counterfactual report.
- [ ] 3.3 Record the transfer conclusion and either reject further live spending for this candidate family or define a separately reviewed next step; do not promote from proxy evidence.
