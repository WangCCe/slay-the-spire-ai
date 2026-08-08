from __future__ import annotations

import hashlib
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

CONSUMED_CROSS_FITTED_APPROVAL_ARTIFACTS = {
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260806_r1/registration.json": (
        63171200,
        "1a3b267c16524e1e0449a8bddbd482684fb9dd0ac89c20bd9db19a9bd755249c",
    ),
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260806_r1/external_approval.json": (
        577,
        "1355834abdca755bc9ad84179410af800d2d44b9c7f50b919f258021832b1143",
    ),
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260806_r1/authorization.json": (
        1519,
        "307fd655305d258819660438a2e04cad02e10734b38cc2ce24e01b8aacbecc7c",
    ),
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260806_r1/terminal.json": (
        1740,
        "39aa5ae15b624cae49dc3c4f04df5d8b2de2ae47b7d52cbbfb665f467a2abd75",
    ),
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260806_r1/artifact_manifest.json": (
        4864,
        "16fc63bf40075396f7f3dd7e1380fe371e993afb8677c2728cf7f1adaae23675",
    ),
}


def test_consumed_hierarchical_source_and_terminal_evidence_are_byte_preserved():
    for relative_path in CONSUMED_HIERARCHICAL_PATHS:
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative_path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert (ROOT / relative_path).read_bytes() == committed, relative_path


def test_consumed_cross_fitted_v1_approval_evidence_is_byte_preserved():
    for relative_path, (size_bytes, expected_sha256) in (
        CONSUMED_CROSS_FITTED_APPROVAL_ARTIFACTS.items()
    ):
        payload = (ROOT / relative_path).read_bytes()
        assert len(payload) == size_bytes, relative_path
        assert hashlib.sha256(payload).hexdigest() == expected_sha256, relative_path
