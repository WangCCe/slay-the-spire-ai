# Card-only baseline clipping ablation postmortem

## Result

The one-step ablation completed successfully with verdict
`baseline_clipping_not_material_in_one_step`.

- Environment accesses: `64`
- Supported trajectories: `63/64`
- Censored trajectories: `1` known Courier-restock blocker
- Optimizer steps: one clipped branch step and one unclipped branch step
- Current-semantics reproduction: exact
- Reproduced model SHA-256:
  `072bd87ab00fe94cddef3725819a0c9972db1d822ffd03cdcc6166e174006f86`

The exact reproduction of historical checkpoint `005` establishes that shared
trajectory collection, cross-fitted baseline fitting, term reconstruction, Adam
state, and the clipped branch update match the r1 execution.

## Mechanism Evidence

The shared cohort contained `572` card decisions. `124` held-out baseline
predictions were clipped from negative values to zero; the minimum unclipped
prediction was `-0.410625309`.

| Metric | Clipped | Unclipped |
|---|---:|---:|
| Advantage mean | 0.028011118 | 0.052868117 |
| Advantage population stddev | 0.213126732 | 0.238343052 |
| Total loss | -0.003121465 | -0.000059563 |
| Pre-clip gradient norm | 0.031244520 | 0.032265510 |
| Parameter step L2 | 0.146790576 | 0.146799950 |

The applied-gradient cosine was `0.990775956`, above the registered material
boundary of `0.99`. No global gradient clipping occurred in either branch
because both norms were far below the `1.0` ceiling.

On the fixed 175-row probe, the branches had zero exact-action and family
differences. Mean joint total variation was `0.000119916`, below the registered
`0.001` boundary, and mean joint symmetric KL was `0.000000402`. The maximum
row total variation was `0.001527208`.

## Decision

Do not run the proposed four-step clipping ablation. Baseline lower clipping is
observable in the residual arithmetic but is not a material explanation for the
r1 policy's weak behavior sensitivity under the registered one-step criteria.

The next useful experiment should not adjust the clipping threshold or extend
this cohort. The higher-leverage next step is to persist one shared rollout
replay artifact and compare loss/optimizer variants without additional native
environment access. Candidate variants should be limited to mechanisms already
suggested by the function-space evidence, especially representation/optimizer
allocation between hidden and scorer parameters; learning rate alone remains
unsupported.

## Isolation

- CommunicationMod configuration SHA-256 remained
  `7ec79e01f9293a19ead3c59a26b18bb75ef900afa3dbe45d657769fe46061862`.
- Production checkpoint metadata remained `208` files, `1,356,047,034` bytes,
  SHA-256 `c96bb8fddafe40e92936da95f0d2e1c9f8ef2b5f1a8e6d5f6c69e2ba6f96ba1c`.
- Every downstream authority field is false.
- No fresh/protected cohort, CommunicationMod, game process, production model,
  gameplay policy, or promotion path was used.

## Evidence

- `reports/noncombat_card_only_baseline_clipping_ablation_20260813_r1_registration.json`
  (`9679a76283134553ae488d38ced3cdbacc420f4e58e31c0d2fe374ddeeff57a2`)
- `reports/noncombat_card_only_baseline_clipping_ablation_20260813_r1/report.json`
- `reports/noncombat_card_only_baseline_clipping_ablation_20260813_r1/terminal.json`

The two branch checkpoints remain local experiment artifacts and are excluded
from version control and production checkpoint discovery.
