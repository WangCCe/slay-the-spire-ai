# Low-alpha comparison r1 setup failure

The registered interpolation completed, but the matched comparison stopped with `comparison_setup_failure` because `ComparisonConfig` had not been updated for the shared `evaluate_policy` encounter-identity fields. No metrics, pairwise rows, or ranking were published.

The missing attribute is read after environment reset and state mapping inside the first evaluation loop. Therefore the `126000..126255` cohort is conservatively treated as consumed even though the report contains zero outcome rows; it will not be reused.

The repair only adds fixed disabled encounter-identity fields to the comparator config and a focused regression (`8 passed`). It does not change checkpoints, alphas, thresholds, reward, native code, or training. A separately registered r2 comparison must use fresh seeds `127000..127255`.
