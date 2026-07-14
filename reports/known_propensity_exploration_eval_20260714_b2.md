# Known-Propensity Exploration Post-Review Bounded Eval B2 - 2026-07-14

## Scope

- Source commit: `99dd44a6bec3a8fea64af76ddcc8fa587b06e5fd`
- Source state recorded by manifest: tracked clean
- Python: `D:\anaconda\envs\stsai\python.exe`
- Agent command: `main.py --agent combat_rl --elite-route conservative --max-games 25 --ascension 0 --rl-version v2 --eval`
- Exploration rates: `card_reward=1000/10000`, `shop=1000/10000`
- Per-run alternative budget: `2`
- Training: disabled
- Session: `known-propensity-eval-20260714-b2`
- Exact run allowlist: 25 entries in `known_propensity_exploration_eval_20260714_b2_run_allowlist.json`
- Frozen run copies: `known_propensity_exploration_eval_20260714_b2_runs/`

This is the first full bounded batch collected after the callback-transaction,
Java Properties fingerprint, and exact-integer evidence fixes passed review. The
batch stopped at the configured 25-game limit. It did not raise either category
above the 10 percent ceiling or the two-attempt per-run budget to force support.

## Live Result

- Completed runs: `25`
- AI-marked runs: `25`
- First/last run: `1783990089.run` / `1783993176.run`
- Unique joined trajectories: `25`
- Victories: `0`
- Floor distribution: `16=15, 18=1, 24=1, 27=3, 30=1, 33=3, 38=1`
- Terminal `Max games reached (25); exiting.` line: present
- CommunicationMod suspicious rows after the B2 launch marker: `0`
- Remaining Slay the Spire, ModTheSpire, or AI processes after shutdown: `0`

At startup, a stale `start` command was rejected after the game was already in
an event screen. This produced two adjacent ERROR rows at `08:46:32`. The agent
recovered immediately, no later strict ERROR/CRITICAL/traceback row occurred,
and all 25 configured games completed. The exact context is frozen in the log
diagnostics artifact and complete rotating-log captures. This is a bounded-run
startup limitation, not an exploration confirmation or outcome-join failure.

## Evidence Validation

- Proposed records: `230`
- Resolution records: `230`
- Confirmed known-propensity records: `230`
- Replay-valid records: `230`
- Candidate-legal records: `230`
- Verified behavior propensities: `230`
- Exported samples: `230`
- Outcome-matched samples: `230`
- Exclusions: `0`
- Source provenance verified: `true`
- Post-session isolation verified: `true`

Category/arm support among joined samples:

- `card_reward`: baseline `174`, alternative `19`
- `shop`: baseline `30`, alternative `7`

The external pre-session snapshot matches the manifest runtime baseline under
the semantic CommunicationMod configuration comparison. The post-session
snapshot matches the runtime baseline exactly, including all 209 allowlisted
configuration/checkpoint paths. The frozen trace and manifest are byte-for-byte
copies of the stopped live artifacts.

## Qualification Boundary

Known-propensity exploration data ready is `true`; there are no structural
blocking conditions. B2 passes the trajectory minimum, every category/arm
support minimum, confirmation, replay, candidate legality, propensity,
outcome, provenance, and isolation requirements.

This result qualifies the collection dataset, not the gameplay policy. The
machine-readable gate continues to report all downstream decisions as false:

- OPE ready: `false`
- Causal uplift ready: `false`
- Formal non-combat RL training ready: `false`
- Live policy promotion ready: `false`

No policy-quality or causal-effect claim is made. In particular, 25 trajectories
and seven shop alternatives are enough for the registered structural gate, but
not enough to justify a high-variance trajectory estimator or policy update.

## Next Gate

The next change should define non-combat outcome and OPE readiness rather than
start training. It should freeze the reward horizon, censoring rules, trajectory
unit, estimator diagnostics, effective-sample-size floor, and a deterministic
no-promotion report. Training and live promotion must remain blocked until that
change has tests and a fresh holdout evaluation protocol.

## Verification

- Independent evidence reconstruction: `118 checks passed`
- Focused exploration/runtime/evidence pytest: `141 passed`
- Full pytest suite: `2527 passed`
- `openspec validate --all --strict`: `33 passed, 0 failed`
- Initial sandboxed focused pytest: invalid due to Windows basetemp ACL; the
  identical suite passed with a fresh out-of-sandbox basetemp

## Frozen Artifacts

- Config SHA-256: `9bd93cfbbb0c490641288a898078eafcd5ecd06a8c1e763209ed7f65d7a42199`
- Trace SHA-256: `537408d82ac5af9fc43c4179b82a6cbfb0bd6ae47118d1705988010b4fccc688`
- Manifest file SHA-256: `d7eae7afc635a0ed28b227f99c0d01ab9c36d6b861058059d5ec8c31cb2f4c4f`
- Manifest logical hash: `b5fbf4906a7458aaa3a40d6a5b88bdb5a4e07ef514033494cea9af9bcba52c31`
- Effective config hash: `90be978c69e94e2ee8c0e82d46ef711ab4db0e4162f25dc1b82d0a5e846d8092`
- Pre-isolation SHA-256: `92c12d4e8077590e8c53bbbec55dbb80e56f3e3633761e9999e280bbe8a1429a`
- Post-isolation SHA-256: `300ffe755f058b493dd261c040982fa80237d947d061b8238f2d66c2bb6a3f52`
- Run allowlist SHA-256: `c1443104e56759ba2d48553346c69054b2eb8a12769830567779f286b1f96942`
- Samples SHA-256: `b7436b5a7ef12f345e54172f56ecb05b7aefe59f4ed9007805cc20aa4e90820f`
- Export summary SHA-256: `f7881e003f0c4560309c21eb6fe29617152637bdc5df81999961a586ee5bdde8`
- Qualification JSON SHA-256: `dd64a5144b23c6083f2a0f24f1ca544ff966c12cecc2b4147b1dc99623641891`
- Qualification Markdown SHA-256: `53e6deb701ca587543477471d80e877bb10289d40f0e57b48a42f42751c81793`
- AI debug slice gzip SHA-256: `afc3b549948b78e315c1863b3238466fcadf7644faf18e2a8e67897f01d8b841`
- AI debug slice payload SHA-256: `19d41d9e552469d15e8179fe5d77d62857162386c3a95fdc15d5dabed2fb7a87`
- CommunicationMod slice SHA-256: `c2e6e3c7155837b1e0d19080fbe53afa6927c31fd98e43b5e6f7f1980a99871b`
- Log diagnostics SHA-256: `e219ded498dca6a601630a99b9c17d4c3ec2348e9796bb95c89b27b0ee2f9ad7`
- Raw rotating-log index SHA-256: `91d8651590f51b6fd0c5c1ef07d1a34e781e49773293808cff462b9f1f1ad9c1`

These hashes cover the repository-preserved LF bytes. The run allowlist records
the SHA-256, AI marker, and parsed outcome for every input run. The frozen
config, trace, manifest, run copies, isolation snapshots, canonical samples,
qualification outputs, complete raw log slices, rotation chunks, and diagnostics
are stored beside this report.
