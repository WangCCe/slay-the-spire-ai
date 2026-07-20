## 1. Preserve Evidence And Prove The Regression

- [x] 1.1 Replay r2 failure-record self-hash `8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c`, file SHA-256 `3fbace492dd0f849bdf86deff1df97dfc4ae3b77a427545413ac48170c9c2540`, its nine predecessor files, final ten-file root inventory, restored CommunicationMod baseline, absent study root, and unchanged r1 root before editing tracked source.
- [x] 1.2 Add `test_child_handshake_accepts_cold_state_after_45_seconds` in `tests/test_study_handshake.py` using a fake monotonic clock, callback-free fake coordinator, and release-on-ready sleep hook; run only that test with `D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-cold-start-timeout-red-20260717 tests/test_study_handshake.py::test_child_handshake_accepts_cold_state_after_45_seconds -q` and require the current 30-second implementation to fail specifically with `StudyHandshakeError: child readiness deadline exceeded`.

## 2. Implement The Fixed 120-Second Contract

- [x] 2.1 Change only `READINESS_TIMEOUT_SECONDS` in `spirecomm/communication/study_handshake.py` from 30 to 120, rerun the exact regression from 1.2, and require attempt, ready, and release validation to pass without callbacks, exploration, agent creation, gameplay, or wall-clock delay.
- [x] 2.2 Update the independently duplicated launchable contract in `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py` to require literal 120 while preserving literal 10 for release; update exact assertions in `tests/test_study_handshake.py`, `tests/test_noncombat_outcome_evidence_expansion.py`, and `tests/test_noncombat_outcome_evidence_runner.py` from 30 to 120 without weakening malformed, timeout, duplicate, v1 refusal, or ordinary-gameplay tests.
- [x] 2.3 Add or update verifier coverage in `tests/test_noncombat_outcome_evidence_verifier.py` so a launchable registration containing 30 is rejected and the independently reconstructed 120-second contract passes; keep historical schema-v1 fixtures byte-identical and read-only.

## 3. Verify And Review The Fix Offline

- [x] 3.1 Run focused Windows pytest for `tests/test_study_handshake.py`, `tests/test_main_runtime_errors.py`, `tests/test_noncombat_outcome_evidence_expansion.py`, `tests/test_noncombat_outcome_evidence_runner.py`, and `tests/test_noncombat_outcome_evidence_verifier.py` using `-p no:cacheprovider` and a fresh writable repository basetemp; resolve only failures attributable to the timeout-contract change.
- [x] 3.2 Run the full Windows pytest suite with cache disabled and a fresh writable repository basetemp, then run Python compile/import checks for the modified producer, runner, handshake, and verifier modules, `openspec validate --all --strict`, `git diff --check`, and a scan proving no training flag, exploration rate, seed, schedule, threshold, estimator, checkpoint, CommunicationMod Java, or gameplay-policy change entered the diff.
- [x] 3.3 Obtain independent code/spec review of the fake-clock regression, fixed parent/child deadline, verifier independence, historical compatibility, fail-closed behavior, and authority boundary; resolve Critical or Important findings, rerun affected focused tests plus full pytest, and commit the verified fix as one cohesive change without launching Slay the Spire.

## 4. Gate Fresh Live Validation Separately

- [x] 4.1 Update `run-v2-known-propensity-outcome-evidence-study` only after the fix commit: preserve both failed qualification roots, regenerate and independently review the pending v2 registration under the 120-second contract, select a previously absent r3 qualification root, and commit that separate study amendment before any live process starts.
- [ ] 4.2 Run the complete bounded r3 no-action cold-start qualification from the later tracked-clean study candidate and require attempt/ready/release, semantic configuration restoration, unchanged markers/runs/checkpoints/global logs, no gameplay or study artifact, and independent attestation; keep this fix change open and do not authorize `start` if r3 does not pass.

R3 did not pass, and the later r7 replacement retired at `source_validation_failed` before the active request or handshake. This gate remains unsatisfied and `start` remains unauthorized.
