# Known-Propensity Exploration Smoke R5 - 2026-07-14

## Scope

- Source commit: `cdf5b2a1b3c24d09ccaa8404d2aa11d5e014c117`
- Python: `D:\anaconda\envs\stsai\python.exe`
- Agent command: `main.py --agent combat_rl --elite-route conservative --max-games 25 --ascension 0 --rl-version v2 --eval`
- Exploration rates: `card_reward=1000/10000`, `shop=1000/10000`
- Per-run alternative budget: `2`
- Training: disabled
- Exact run allowlist: `1783965043.run`

## Startup Diagnosis

R3 and R4 both created valid manifests but stopped at `Loading RL components...`
before producing a trace. A controlled pipe probe reproduced the hang for more
than 15 seconds when `Coordinator` started its blocking stdin reader before the
lazy RL import. The same import completed in 6.218 seconds when the reader was
deferred while the stdout writer still emitted `ready`.

Commit `cdf5b2a1` keeps the early `ready` signal and starts the stdin reader
after RL agent initialization. R5 loaded the RL components in about 7.05 seconds,
loaded the evaluation checkpoint, started the reader, and entered game 1.

## Live Result

- Completed run: `1783965043.run`
- AI marker: `1783965046`
- Outcome window: `1783964926..1783965043`
- Floor reached: `20`
- Victory: `false`
- Killed by: `3 Byrds`
- Playtime: `117` seconds
- `ai_debug.log`: no ERROR, CRITICAL, or traceback rows in the R5 log
- `communication_mod_errors.log`: no suspicious rows after the R5 launch marker

The batch began a second trajectory before controlled shutdown. Its three
confirmed records are retained as diagnostics with `join_status=missing`; they
are not attributed to the completed run.

## Evidence Validation

- Proposed records: `13`
- Resolution records: `13`
- Confirmed known-propensity records: `13`
- Replay-valid records: `13`
- Candidate-legal records: `13`
- Verified behavior propensities: `13`
- Exported samples: `13`
- Outcome-matched samples: `10`
- Exclusions: `0`
- Source provenance verified: `true`
- Post-session isolation verified: `true`

The completed trajectory contributed nine card-reward baseline samples and one
shop baseline sample. The 10 percent sampler did not select an alternative arm
in this smoke. No rate or budget was raised to force support.

## Qualification Boundary

Known-propensity exploration data ready remains `false`. Current blockers are:

- `insufficient_unique_joined_trajectories`
- `insufficient_card_reward_alternative_support`
- `insufficient_shop_baseline_support`
- `insufficient_shop_alternative_support`

OPE, causal uplift, formal non-combat RL training, and live policy promotion all
remain blocked.

## Frozen Artifacts

- Config SHA-256: `584c1a85f86b60d5ae3c95038c44a62ef2284b1faeaca96e89bdfc525bc92184`
- Trace SHA-256: `fea7fd30f0166b6e532f60fbf6f88ce3e911166603e7606be2afbf6d3ee9db92`
- Manifest file SHA-256: `3d24e92c62da142eb51e52a53b35e5f8b04828711d56e98c0481e68c4d5650e7`
- Manifest logical hash: `782e92172a37d1f98cbe2890db9865ee23ed2449f20fcf1d191125f41a0a7933`
- Effective config hash: `225abbd2e6170ba294bf4ad056d76fe80138b973abb89e2116dcb3925388f8ed`
- Pre-isolation SHA-256: `4c196c3690b5b92bb48f08fb8241d684c97d01911530d3df0c851e4938e7cf2b`
- Post-isolation SHA-256: `0e65c361d554962698e9f39d01d82f5bbe92ea2457f0e3d1c43f125cda772d61`
- Run SHA-256: `abeaf37ca760982aedc2b2aa5f83c32a4b8c58772f4e49ccb12882eb80f185b8`
- Samples SHA-256: `d03423892cc7cd6fdb32ed3c09318d662929a39d425629884dad034f74697161`
- Export summary SHA-256: `1998a30d2ff4ffca0408a769f48a01c8beff672330b330a7a7bbeae03fcf689a`
- Qualification JSON SHA-256: `60e3b91e3c0df98506f467436397c0c72574fc11941bf69ff71cf2073cca368f`
- Qualification Markdown SHA-256: `d49454092d46238c6140d7c20e46ce6983221b74a9c14840604d6a27d533d9a1`

The frozen trace, manifest, run, isolation snapshots, exported samples, export
summary, and qualification outputs are stored beside this report.
