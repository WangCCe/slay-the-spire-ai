# Known-Propensity Exploration Bounded Eval B1 - 2026-07-14

## Scope

- Source commit: `33793b9808da2cccfce9874e4fc5f789372783a6`
- Source state recorded by manifest: tracked clean
- Python: `D:\anaconda\envs\stsai\python.exe`
- Agent command: `main.py --agent combat_rl --elite-route conservative --max-games 25 --ascension 0 --rl-version v2 --eval`
- Exploration rates: `card_reward=1000/10000`, `shop=1000/10000`
- Per-run alternative budget: `2`
- Training: disabled
- Session: `known-propensity-eval-20260714-b1`
- Exact run allowlist: 25 entries in `known_propensity_exploration_eval_20260714_b1_run_allowlist.json`
- Frozen run copies: `known_propensity_exploration_eval_20260714_b1_runs/`

The batch stopped at the configured 25-game limit. It did not raise either
category above the 10 percent ceiling or the two-attempt per-run budget to force
qualification support.

## Live Result

- Completed runs: `25`
- AI-marked runs: `25`
- First/last run: `1783965503.run` / `1783968413.run`
- Unique joined trajectories: `25`
- Victories: `0`
- Floor distribution: `14=1, 16=13, 21=1, 24=1, 27=1, 29=1, 31=1, 33=6`
- Terminal `Max games reached (25); exiting.` line: present
- CommunicationMod suspicious rows after the B1 launch marker: `0`

At startup, a stale `start` command was rejected after the game was already in
an event screen. This produced two adjacent ERROR rows at `01:56:42`. The agent
recovered immediately, no later strict ERROR/CRITICAL/traceback rows occurred,
and all 25 configured games completed. The exact context is frozen in the log
diagnostics artifact; this is a batch limitation, not evidence of a propensity
or outcome-join failure.

## Evidence Validation

- Proposed records: `243`
- Resolution records: `243`
- Confirmed known-propensity records: `243`
- Replay-valid records: `243`
- Candidate-legal records: `243`
- Verified behavior propensities: `243`
- Exported samples: `243`
- Outcome-matched samples: `243`
- Exclusions: `0`
- Source provenance verified: `true`
- Post-session isolation verified: `true`

Category/arm support among joined samples:

- `card_reward`: baseline `181`, alternative `20`
- `shop`: baseline `38`, alternative `4`

The external pre-session snapshot matches the manifest runtime baseline under
the semantic CommunicationMod configuration comparison. The post-session
snapshot matches the runtime baseline exactly, including all allowlisted combat
checkpoints.

## Qualification Boundary

Known-propensity exploration data ready remains `false`. The only structural
blocker is:

- `insufficient_shop_alternative_support` (`4`, minimum `5`)

The trajectory minimum, confirmation, replay, candidate-legality, propensity,
outcome, provenance, and isolation requirements all pass. OPE, causal uplift,
formal non-combat RL training, and live policy promotion remain explicitly
blocked; this report makes no policy-quality or causal-effect claim.

## Frozen Artifacts

- Config SHA-256: `35e2cbaf91e6633019a7f8975cc42df3519c60a39701b48e805bca569e07a99f`
- Trace SHA-256: `ec56f1ffdd503246e6ed4fb94ced324a33a87f86b8fa7b992c611bd6c1c86c6b`
- Manifest file SHA-256: `1aa787dd2976dc48e0d0e7b99326536c5eeaa22d56355018db751a81ac95293d`
- Manifest logical hash: `11b586057c20c9a334d305f1be90e29fcee383bb544d6ef0aa607e5975b584ea`
- Effective config hash: `07a588bf13723a003144e80d296f0e3ded473814020df85160fce07eeab1f0c9`
- Pre-isolation SHA-256: `33cce6ac1752d614f8c8d96adccdae0a7bd144390c5dfcb6b8d0745f944071c6`
- Post-isolation SHA-256: `bf26b7a573e3048d9eabcb97da89b351c9ede2344680b04fdb08a9e3304aefde`
- Run allowlist SHA-256: `071488f810b5106e2ba343b8d5f745fa4f3ec4936587edd42c545725ff9e5d51`
- Samples SHA-256: `c15352fb18bf0b3b9386c3e4801007bf40318dd5f49b9f64de178cc5d407e5f1`
- Export summary SHA-256: `2e9c3c6a48cafb403183d9ab7f0f66b9ef03c168ce3cb117381c3341a17ac910`
- Qualification JSON SHA-256: `8819d06069f53ba397812871dba0b52329d6e9d22e2f8a09abf6ac60de27f12a`
- Qualification Markdown SHA-256: `5cbbbdda7724ae0c28879ce506d0a045148248b26ca0560f94532943e809c997`
- Log diagnostics SHA-256: `425b7c6c5295c94817d64d30ec39dbbd8a2e0826798454d9a82caeb72945eb20`

These hashes cover the repository-preserved LF bytes. The scoped
`.gitattributes` rules prevent Windows checkout conversion from changing the
frozen evidence after commit.

The run allowlist records the SHA-256, AI marker, and parsed outcome for every
input run. The frozen trace, manifest, run copies, isolation snapshots, samples,
export summary, qualification outputs, and log diagnostics are stored beside
this report.
