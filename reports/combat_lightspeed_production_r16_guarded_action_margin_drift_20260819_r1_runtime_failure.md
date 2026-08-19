# Guarded action-margin audit r1 runtime failure

The registered r1 audit stopped during fresh transition collection on `unknown_relic_identity: Sling`. No drift report or output directory was published, and candidate Q inference had not started.

Because native states from `132000..132255` had already been accessed, the cohort is consumed and will not be reused. The repair is a narrow fail-closed alias from native `Sling` to canonical `Sling of Courage`; the complete LightSTS bridge test file passed `20 passed, 4 skipped` after the change.

A new audit requires a new registration, updated bridge source hash, and fresh seeds.
