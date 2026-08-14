## 1. Runtime Boundary

- [x] 1.1 Add regression coverage for an inert, source-bound 1-to-25-game evaluation configuration and three-way mode exclusion.
- [x] 1.2 Reuse the canary substitution/fallback runtime under a distinct evaluation schema, environment variable, and row schema.
- [x] 1.3 Forward the explicit evaluation configuration through `main.py` and `scripts/run_training_batch.py`.

## 2. Verification

- [x] 2.1 Run the card-uplift focused pytest files and validate the OpenSpec change (`31 passed`; strict validation passed).
- [x] 2.2 Run the repository commit gate once after focused verification (`4567 passed`, `17 skipped`, and three pre-existing historical baseline-lineage failures in files untouched by this change; no retry).
- [x] 2.3 Commit and push the source-bound live-evaluation capability (`1b2030022`).

## 3. Fresh Gameplay Evidence

- [x] 3.1 Register a 10-game fresh evaluation configuration bound to the committed source and frozen candidate artifacts.
- [x] 3.2 Save the ordinary CommunicationMod configuration, run and monitor the fresh candidate cohort, then restore the saved bytes.
- [x] 3.3 Publish run, intervention, error, latency, victory, isolation, and rollback evidence and classify the next decision.
