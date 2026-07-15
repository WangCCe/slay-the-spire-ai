# Non-Combat Outcome Evidence Expansion Registration Review

Date: 2026-07-15

Status: `FROZEN_PRE_COLLECTION`

This report freezes the registered implementation and its no-game verification
evidence. No registered game has started. The external artifact root, run lock,
and study ledger do not exist.

## Registration Identity

- Study ID: `noncombat-outcome-evidence-expansion-20260715`
- Schema: `noncombat-outcome-evidence-registration-v1`
- Registration: `reports/noncombat_outcome_evidence_expansion_20260715_registration.json`
- Artifact root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260715`
- Canonical registration hash: `adf850f96537f01ae29f99d45a56c1d9ffcddecc33665e4c76680515ca6631c2`
- Registration file SHA-256: `c0a0b2cf1545965ebca8b24aa2193cc70c8d173ffc71fd993b839b7dbf30f215`
- Registration bytes: `18881`
- Canonical line ending: `LF`

The registration contains 24 ordered 25-attempt slots, 600 scheduled attempts,
session IDs `s01` through `s24`, and seeds `2026071501` through `2026071524`.
The behavior rates are `card_reward=300` and `shop=1000` basis points with a
two-alternative-attempt per-run budget. The only executable alternatives are
`card_reward:skip` and `shop:leave`; event and route remain shadow-only.

The command is fixed to Windows Python and eval-only execution:

```text
D:\anaconda\envs\stsai\python.exe D:\PycharmProjects\slay-the-spire-ai\main.py --agent combat_rl --elite-route conservative --max-games 25 --ascension 0 --rl-version v2 --eval
```

The evidence thresholds are 575 complete trajectories, 50 baseline and 50
alternative decisions per executable category, at least one half nonzero
deterministic-Current trajectory weight, ESS fraction at least 0.5, maximum
normalized weight at most 0.05, and at least three supported victories. The
registered analysis remains fixed to deterministic Current, 10,000 bootstrap
replicates, 95 percent confidence, and the committed calibration artifact.

An exact-key scan found no observed outcome or policy-evaluation fields such as
`victory`, `floor_reached`, `killed_by`, `target_weight`, `ess`, `estimate`,
bootstrap rows, influence rows, or comparison gates. Registered thresholds and
output filenames are design inputs, not observed study results.

## Canonical Replay

The production loader and canonical renderer replayed the committed candidate
bytes exactly:

```text
canonical_equal=true
slot_count=24
scheduled_attempts=600
first_session_id=noncombat-outcome-evidence-expansion-20260715-s01
last_session_id=noncombat-outcome-evidence-expansion-20260715-s24
first_seed=2026071501
last_seed=2026071524
forbidden_observed_keys=[]
```

No-game dry-run command:

```text
D:\anaconda\envs\stsai\python.exe scripts\run_noncombat_outcome_evidence_expansion.py dry-run --registration reports\noncombat_outcome_evidence_expansion_20260715_registration.json
```

Result: exit 0 with exactly 24 ordered launches. Every launch used the registered
session, seed, paths, `card_reward=300`, `shop=1000`, budget 2, `--max-games 25`,
and `--eval`; no training or mutation flag was present. Dry-run created no config,
manifest, trace, run-lock, ledger, or gameplay artifact.

## Verification

Focused Windows pytest:

```text
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-outcome-prelock-focused-20260715 tests/test_noncombat_outcome_evidence_expansion.py tests/test_noncombat_outcome_evidence_runner.py tests/test_noncombat_outcome_evidence_pool.py tests/test_noncombat_outcome_evidence_gate.py tests/test_noncombat_outcome_evidence_finalizer.py tests/test_noncombat_outcome_evidence_verifier.py tests/test_noncombat_exploration_evidence.py tests/test_noncombat_ope_readiness.py tests/test_noncombat_ope_estimation.py tests/test_noncombat_ope_bootstrap.py tests/test_noncombat_ope_influence.py tests/test_noncombat_ope_estimate_artifacts.py tests/test_noncombat_ope_artifact_verifier.py tests/test_noncombat_ope_estimate_verifier.py tests/test_noncombat_ope_calibration.py
```

Result: `299 passed in 263.75s`.

Full Windows pytest:

```text
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-outcome-prelock-full-20260715
```

Result: `2777 passed in 306.31s`.

Additional checks:

- `openspec validate --all --strict`: 36 passed, 0 failed.
- `git diff --check`: exit 0; only autocrlf notices, with no whitespace error.
- `git check-attr text eol`: every run-lock implementation path and both
  registration report paths resolve to `text: set`, `eol: lf`.
- Canonical registration byte/hash replay: exact.
- No-game dry-run: 24/24 registered slots, exact command/config replay.
- Complete runner file: `53 passed in 10.27s`.

The previously frozen inputs remain byte-identical:

- OPE readiness implementation: `b62bd274c41a56ad3721c5390736c9d19171fe6037fd8edb278f848f3adf677d`
- OPE estimator implementation: `39e4b981348918ec8ab3e18c23f62f261be6a905d4b4c9826cfc3cae7e8bf370`
- Estimate artifact implementation: `2486b7589b221193059e615ff3a6c5aa4573cd5017e800adfec8f51e9a52b98e`
- Calibration artifact: `a7ac2ca9c2a0644125323769c6fcf6225295d4d6ec903995a5d332300a0eaf3f`

## Review Closeout

Accepted review findings were resolved with regressions:

- Direct script execution now anchors imports to the registration repository.
- Registrations from another checkout are rejected.
- Run-lock-controlled source and registration artifacts have explicit LF rules.
- A tracked, run-lock-hashed `analysis_scripts/__init__.py` prevents directory,
  ZIP, or egg packages on `PYTHONPATH` from shadowing registered analysis code.

The ZIP-shadow regression was observed failing before the fix and then passed.
Final independent review reported no remaining Critical or Important finding.

## Pre-Lock Protocol Correction

Task 7.1 inspection of the local CommunicationMod source found that every line
from child stdout is queued as a game command. The registered `run-next` wrapper
previously printed its final audit JSON to stdout after the AI child exited,
which would inject one invalid command at the end of each slot. A regression was
observed failing, then `run-next` alone was changed to emit its final audit JSON
to stderr. The other offline subcommands retain machine-readable stdout.

The correction changes a run-lock-controlled implementation byte but does not
change registration fields, schedule, behavior, thresholds, or analysis rules.
Canonical registration replay remains exact with registration hash
`adf850f96537f01ae29f99d45a56c1d9ffcddecc33665e4c76680515ca6631c2`
and file SHA-256
`c0a0b2cf1545965ebca8b24aa2193cc70c8d173ffc71fd993b839b7dbf30f215`.

## Task 7.1 Preflight

- Stale Slay the Spire, Java, and Python processes: none.
- CommunicationMod config semantic SHA-256:
  `961d8df7edd68461feebb830ee700a012f8bccf994ed00ea4eeae5a978c6d06d`.
- CommunicationMod outer command: Windows production Python plus the registered
  `run-next` wrapper and canonical registration path.
- Registered child command: Windows production Python, `--max-games 25`,
  `--eval`, and no `--train` or mutation flag.
- Checkpoint inventory: 208 files, 1,356,047,034 bytes.
- Checkpoint snapshot SHA-256:
  `4d5c96bebb9f441f9f19479835f17a193edefb6fb279e24e47743e790825f20c`.
- Previous CommunicationMod config backup:
  `C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties.pre-outcome-evidence-20260715.bak`.

## Collection Boundary

The only allowed future run-lock HEAD is the clean commit containing this report,
the canonical registration, the implementation, and completed Task 7.1
bookkeeping. Its SHA is intentionally not embedded in tracked content because that
would be self-referential; Task 7.2 must capture and verify the actual clean HEAD
in the external immutable run lock. No earlier commit and no later dirty or changed
tree is eligible.

At the completed Task 7.1 pre-lock boundary:

- external artifact root: absent
- run lock: absent
- study ledger: absent
- registered games launched: zero
- gameplay or training process started by this work: no
- CommunicationMod configuration: study wrapper, captured by semantic hash above
- checkpoint changed by this work: no

Task 7.2 remains a separate run-lock transition. This report does not
authorize training, gameplay-policy edits, causal uplift claims, or promotion.
