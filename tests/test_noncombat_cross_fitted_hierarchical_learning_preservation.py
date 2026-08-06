from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CONSUMED_HIERARCHICAL_PATHS = (
    "analysis_scripts/noncombat_hierarchical_simulator_learning_experiment.py",
    "analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py",
    "analysis_scripts/verify_noncombat_hierarchical_simulator_learning_experiment.py",
    "reports/noncombat_hierarchical_simulator_learning_successor_20260806_registration.json",
    "reports/noncombat_hierarchical_simulator_learning_successor_20260806_authorization.json",
    "reports/noncombat_hierarchical_simulator_learning_successor_20260806/bootstrap_runtime.json",
    "reports/noncombat_hierarchical_simulator_learning_successor_20260806/checkpoints/checkpoint_0008.json",
    "reports/noncombat_hierarchical_simulator_learning_successor_20260806/terminal.json",
    "reports/noncombat_hierarchical_simulator_learning_successor_20260806/artifact_manifest.json",
)


def test_consumed_hierarchical_source_and_terminal_evidence_are_byte_preserved():
    for relative_path in CONSUMED_HIERARCHICAL_PATHS:
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative_path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert (ROOT / relative_path).read_bytes() == committed, relative_path
