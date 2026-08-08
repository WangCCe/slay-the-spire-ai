"""Source-only baseline-support audit for the sealed cross-fitted r2 run."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
import gzip
import hashlib
import io
import json
import math
from numbers import Real
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any, BinaryIO


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis_scripts import (  # noqa: E402
    verify_noncombat_cross_fitted_hierarchical_learning_experiment as verifier,
)


AUDIT_SCHEMA_VERSION = "noncombat-cross-fitted-baseline-support-audit-v1"
LEASE_SCHEMA_VERSION = "noncombat-cross-fitted-hierarchical-learning-lease-v1"
EVIDENCE_COMMIT = "7f2f08878e08d9276425f2fb99a97cf095361c9e"
LOGICAL_EXECUTION_ID = (
    "noncombat-cross-fitted-hierarchical-learning-successor-20260808-r2"
)
EXPECTED_IDENTITY = {
    "authorization_sha256": (
        "80dffa2fa2c1d1a9d68d638276c73730415842f085c7d881609a37114d88152f"
    ),
    "logical_execution_id": LOGICAL_EXECUTION_ID,
    "registration_sha256": (
        "9d792cadbece4ea21768386904633ebded2e94525fb186bdcbf4a4d7729dbdf9"
    ),
    "request_sha256": (
        "6257a36c6573c8c412bb8727736e81b063dd0c7076f1ea5b41a70d4a08206c2e"
    ),
}
EXPECTED_TERMINAL_FILE_SHA256 = (
    "fff36b367fff09c4efd887db2a33d4cd98fd54b3af358ede397587e773282ce1"
)
EXPECTED_TERMINAL_SHA256 = (
    "3de29ce568b0d418f4e1052c4b7c92040d2de316e035b455c47384daf48db1e0"
)
EXPECTED_MANIFEST_FILE_SHA256 = (
    "9ae80569dc405d17da7d18f277dcebfb280eb40052cb318a19c629fd97cbac75"
)
EXPECTED_MANIFEST_SHA256 = (
    "b563fe8f95fa705ffcf7eafe14c40672599e46ad2a611db6f473a654ec8860eb"
)
EXPECTED_POSTMORTEM_SHA256 = (
    "b2fd8de1fcc190553158710786ab950976c41c2643459b9083aa9c8dfebf0c95"
)
EXPECTED_VERDICT = "experiment_completed_with_cross_fitted_mechanism_evidence"

DEFAULT_SOURCE_PATH = "analysis_scripts/audit_cross_fitted_baseline_support.py"
DEFAULT_TEST_PATH = "tests/test_audit_cross_fitted_baseline_support.py"
DEFAULT_SPEC_PATH = (
    "openspec/changes/audit-cross-fitted-baseline-support/specs/"
    "noncombat-cross-fitted-baseline-support-audit/spec.md"
)
DEFAULT_TERMINAL_ROOT = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2"
)
DEFAULT_POSTMORTEM_PATH = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_"
    "20260808_r2_postmortem.json"
)
DEFAULT_JSON_NAME = "noncombat_cross_fitted_baseline_support_audit_20260809.json"
DEFAULT_MARKDOWN_NAME = (
    "noncombat_cross_fitted_baseline_support_audit_20260809.md"
)

MAX_GZIP_STORED_BYTES = 64 * 1024 * 1024
MAX_GZIP_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
SUPPORT_MINIMUM_ROWS = 64
SUPPORT_MINIMUM_SIDE_ROWS = 16
FAMILY_ENTROPY_COEFFICIENT = 0.01
CONDITIONAL_ENTROPY_COEFFICIENT = 0.01
PREDICTION_MIN = 0.0
PREDICTION_MAX = 3.0
FLOAT_ATOL = 1e-12

AUTHORITY_NAMES = (
    "causal_claim",
    "cohort_materialization",
    "communication_mod",
    "environment_construction",
    "evaluation",
    "execution",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "model_loading",
    "native_loading",
    "ope",
    "policy_promotion",
    "qualification",
    "replay",
    "seed_access",
    "training",
)

LIMITATIONS = (
    "Baseline clipping and direct logit pressure are descriptive properties of "
    "the consumed simulator trajectories, not causal effects.",
    "Direct take-logit pressure is a row-local factorized coordinate, not the "
    "full shared-parameter network gradient.",
    "Repeated decisions within a trajectory are not independent samples.",
    "The audit estimates no policy value, OPE quantity, confidence interval, "
    "target-supported outcome, or live-game effect.",
    "No verdict authorizes fitting, training, replay, evaluation, model loading, "
    "gameplay, qualification, or promotion.",
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT_RE = re.compile(r"[0-9a-f]{40,64}\Z")


class AuditError(ValueError):
    """Raised when immutable evidence or audit arithmetic is invalid."""


def audit_authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def _reject_constant(value: str) -> None:
    raise AuditError(f"JSON contains non-finite constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError(f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def canonical_json_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AuditError(f"value is not canonical JSON: {exc}") from exc


def parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} must be a JSON object")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AuditError(f"{label} must be an object")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise AuditError(f"{label} must be an array")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise AuditError(f"{label} must be an integer >= {minimum}")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise AuditError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise AuditError(f"{label} must be finite")
    return result


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise AuditError(f"{label} must be a lowercase SHA-256")
    return value


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_binding(path: Path, *, relative_path: str) -> dict[str, Any]:
    target = _regular_file(path, relative_path)
    raw = target.read_bytes()
    return {
        "path": PurePosixPath(relative_path).as_posix(),
        "sha256": _digest(raw),
        "size_bytes": len(raw),
    }


def _is_reparse_point(path: Path) -> bool:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise AuditError(f"cannot inspect path: {path}") from exc
    return bool(
        getattr(observed, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _regular_file(path: Path, label: str) -> Path:
    target = Path(path)
    try:
        observed = target.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        not stat.S_ISREG(observed.st_mode)
        or target.is_symlink()
        or _is_reparse_point(target)
    ):
        raise AuditError(f"{label} must be a regular non-symlink file")
    return target


def _git(repo_root: Path, *args: str, allow_failure: bool = False) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 and not allow_failure:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AuditError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def verify_pushed_source(
    repo_root: Path, source_commit: str
) -> dict[str, Any]:
    if _COMMIT_RE.fullmatch(source_commit) is None:
        raise AuditError("source commit is invalid")
    head = _git(repo_root, "rev-parse", "HEAD").decode().strip()
    remote = _git(repo_root, "rev-parse", "origin/master").decode().strip()
    resolved = _git(repo_root, "rev-parse", source_commit).decode().strip()
    if head != resolved or remote != resolved:
        raise AuditError("HEAD, origin/master, and source commit must match")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EVIDENCE_COMMIT, resolved],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise AuditError("source commit does not descend from r2 evidence")
    for args in (("diff", "--quiet"), ("diff", "--cached", "--quiet")):
        completed = subprocess.run(
            ["git", *args], cwd=repo_root, capture_output=True, check=False
        )
        if completed.returncode != 0:
            raise AuditError("tracked worktree must be clean")

    paths = (
        DEFAULT_SOURCE_PATH,
        DEFAULT_TEST_PATH,
        DEFAULT_SPEC_PATH,
        "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py",
    )
    bindings: dict[str, dict[str, Any]] = {}
    for relative in paths:
        working = _regular_file(repo_root / relative, relative).read_bytes()
        committed = _git(repo_root, "show", f"{resolved}:{relative}")
        if working != committed:
            raise AuditError(f"working source differs from commit: {relative}")
        bindings[relative] = {
            "path": relative,
            "sha256": _digest(working),
            "size_bytes": len(working),
        }
    return {
        "evidence_commit": EVIDENCE_COMMIT,
        "source_commit": resolved,
        "source_files": bindings,
    }


def validate_verifier_result(verification: Mapping[str, Any]) -> None:
    if (
        verification.get("verdict") != EXPECTED_VERDICT
        or verification.get("terminal_sha256") != EXPECTED_TERMINAL_SHA256
        or verification.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256
        or verification.get("completed_chunk_indices") != list(range(8))
        or verification.get("checkpoint_count") != 8
    ):
        raise AuditError("independent verifier result mismatch")


def _lock_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise AuditError("execution lease is active") from exc
    else:
        import fcntl

        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise AuditError("execution lease is active") from exc


def _unlock_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def hold_inactive_lease(path: Path) -> Iterator[bytes]:
    target = _regular_file(path, "execution lease")
    with target.open("r+b") as handle:
        _lock_file(handle)
        try:
            handle.seek(0)
            before = handle.read()
            lease = verifier._parse_canonical_json(before, label="execution lease")
            if (
                lease.get("schema_version") != LEASE_SCHEMA_VERSION
                or lease.get("identity") != EXPECTED_IDENTITY
            ):
                raise AuditError("execution lease identity mismatch")
            yield before
            handle.seek(0)
            if handle.read() != before:
                raise AuditError("execution lease changed during audit")
        finally:
            _unlock_file(handle)


def forbidden_loaded_modules() -> list[str]:
    prefixes = (
        "torch",
        "spirecomm",
        "sts_lightspeed_noncombat_adapter",
        "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment",
        "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime",
        "analysis_scripts.noncombat_simulator_adapter",
    )
    return sorted(
        name
        for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)
    )


def validate_baseline_row(row: Mapping[str, Any], label: str) -> str:
    prediction = _mapping(row.get("prediction"), f"{label}.prediction")
    unclipped = _finite(prediction.get("unclipped"), f"{label}.unclipped")
    clipped = _finite(prediction.get("clipped"), f"{label}.clipped")
    baseline = _finite(
        row.get("baseline_prediction"), f"{label}.baseline_prediction"
    )
    expected = min(PREDICTION_MAX, max(PREDICTION_MIN, unclipped))
    was_clipped = prediction.get("was_clipped")
    if not isinstance(was_clipped, bool):
        raise AuditError(f"{label}.was_clipped must be Boolean")
    if (
        not math.isclose(clipped, expected, rel_tol=0.0, abs_tol=FLOAT_ATOL)
        or not math.isclose(baseline, clipped, rel_tol=0.0, abs_tol=FLOAT_ATOL)
        or was_clipped != (unclipped < PREDICTION_MIN or unclipped > PREDICTION_MAX)
    ):
        raise AuditError(f"{label} prediction clipping mismatch")
    raw_return = _finite(row.get("raw_return"), f"{label}.raw_return")
    advantage = _finite(row.get("advantage"), f"{label}.advantage")
    if not math.isclose(
        advantage,
        raw_return - baseline,
        rel_tol=0.0,
        abs_tol=FLOAT_ATOL,
    ):
        raise AuditError(f"{label} advantage identity mismatch")
    if unclipped < PREDICTION_MIN:
        return "clipped_low"
    if unclipped > PREDICTION_MAX:
        return "clipped_high"
    return "unclipped"


def validate_fold_rows(
    rows: Sequence[Mapping[str, Any]],
    fold_trajectories: Mapping[str, Sequence[str]],
    models: Mapping[str, Mapping[str, Any]],
    *,
    expected_held_out: int,
    expected_fit: int,
) -> None:
    if len(fold_trajectories) != 4:
        raise AuditError("baseline must contain exactly four folds")
    all_trajectories: set[str] = set()
    normalized_folds: dict[str, tuple[str, ...]] = {}
    for fold_id, raw_ids in sorted(fold_trajectories.items()):
        ids = tuple(raw_ids)
        if len(ids) != expected_held_out or len(set(ids)) != len(ids):
            raise AuditError(f"{fold_id} held-out trajectories mismatch")
        if all_trajectories.intersection(ids):
            raise AuditError("held-out trajectory folds overlap")
        all_trajectories.update(ids)
        normalized_folds[fold_id] = ids
    if set(normalized_folds) != set(models):
        raise AuditError("baseline model fold inventory mismatch")
    fit_by_fold: dict[str, tuple[str, ...]] = {}
    for fold_id, model in models.items():
        fit_ids = tuple(_sequence(model.get("fit_trajectory_ids"), "fit trajectories"))
        if len(fit_ids) != expected_fit or len(set(fit_ids)) != len(fit_ids):
            raise AuditError(f"{fold_id} fit trajectories mismatch")
        if set(fit_ids).intersection(normalized_folds[fold_id]):
            raise AuditError(f"{fold_id} fit trajectories include held-out rows")
        if set(fit_ids) != all_trajectories.difference(normalized_folds[fold_id]):
            raise AuditError(f"{fold_id} fit trajectories are not the complement")
        fit_by_fold[fold_id] = fit_ids
    for index, raw_row in enumerate(rows):
        row = _mapping(raw_row, f"decision[{index}]")
        fold_id = row.get("fold_id")
        trajectory_id = row.get("trajectory_id")
        if (
            not isinstance(fold_id, str)
            or fold_id not in normalized_folds
            or not isinstance(trajectory_id, str)
            or trajectory_id not in normalized_folds[fold_id]
        ):
            raise AuditError(f"decision[{index}] held-out fold mismatch")
        row_fit = tuple(
            _sequence(
                row.get("baseline_fit_trajectory_ids"),
                f"decision[{index}] fit trajectories",
            )
        )
        if row_fit != fit_by_fold[fold_id] or trajectory_id in row_fit:
            raise AuditError(f"decision[{index}] fit trajectories mismatch")


def _entropy(probabilities: Sequence[float]) -> float:
    if not probabilities:
        raise AuditError("conditional family has no candidates")
    if not math.isclose(math.fsum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise AuditError("conditional probabilities do not sum to one")
    return -math.fsum(p * math.log(p) for p in probabilities if p > 0.0)


def direct_take_pressure(
    row: Mapping[str, Any], *, total_chunk_decisions: int
) -> dict[str, float]:
    if total_chunk_decisions <= 0:
        raise AuditError("chunk decision count must be positive")
    diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
    probabilities = _mapping(
        diagnostic.get("family_probabilities"), "family probabilities"
    )
    if "take" not in probabilities:
        raise AuditError("card reward lacks take family")
    take_probability = _finite(probabilities["take"], "take probability")
    if not 0.0 < take_probability < 1.0:
        raise AuditError("take probability must be interior")
    conditional = _mapping(
        diagnostic.get("conditional_probabilities"), "conditional probabilities"
    )
    family_candidates: dict[str, list[float]] = defaultdict(list)
    for raw_candidate in _sequence(diagnostic.get("candidates"), "candidates"):
        candidate = _mapping(raw_candidate, "candidate")
        action_id = candidate.get("action_id")
        family = candidate.get("kind")
        if not isinstance(action_id, str) or not isinstance(family, str):
            raise AuditError("candidate identity is invalid")
        family_candidates[family].append(
            _finite(conditional.get(action_id), f"conditional {action_id}")
        )
    entropies = {
        family: _entropy(values) for family, values in family_candidates.items()
    }
    expected_conditional_entropy = math.fsum(
        _finite(probability, f"family probability {family}") * entropies[family]
        for family, probability in probabilities.items()
    )
    terms = _mapping(row.get("policy_terms"), "policy terms")
    family_entropy = _finite(terms.get("family_entropy"), "family entropy")
    selected_family = diagnostic.get("selected_family")
    advantage = _finite(row.get("advantage"), "cross-fitted advantage")
    policy = advantage * (
        (1.0 if selected_family == "take" else 0.0) - take_probability
    ) / total_chunk_decisions
    family_regularizer = (
        -FAMILY_ENTROPY_COEFFICIENT
        * take_probability
        * (math.log(take_probability) + family_entropy)
        / total_chunk_decisions
    )
    conditional_regularizer = (
        CONDITIONAL_ENTROPY_COEFFICIENT
        * take_probability
        * (entropies["take"] - expected_conditional_entropy)
        / total_chunk_decisions
    )
    return {
        "combined": policy + family_regularizer + conditional_regularizer,
        "conditional_entropy": conditional_regularizer,
        "expected_conditional_entropy": expected_conditional_entropy,
        "family_entropy": family_regularizer,
        "policy": policy,
        "take_conditional_entropy": entropies["take"],
        "take_probability": take_probability,
    }


def support_status(
    *,
    total: int,
    clipped: int,
    unclipped: int,
    selected_take: int,
    selected_skip: int,
    require_clipping_contrast: bool,
    require_take_skip: bool,
) -> str:
    if total < SUPPORT_MINIMUM_ROWS:
        return "insufficient"
    if require_clipping_contrast and (
        clipped < SUPPORT_MINIMUM_SIDE_ROWS
        or unclipped < SUPPORT_MINIMUM_SIDE_ROWS
    ):
        return "insufficient"
    if require_take_skip and (
        selected_take < SUPPORT_MINIMUM_SIDE_ROWS
        or selected_skip < SUPPORT_MINIMUM_SIDE_ROWS
    ):
        return "insufficient"
    return "supported"


def classify_verdict(
    *,
    global_supported: bool,
    clipped_pressure: float,
    unclipped_pressure: float,
    final_window_unclipped_pressures: Sequence[float],
    final_window_supported: Sequence[bool],
) -> str:
    if (
        not global_supported
        or len(final_window_unclipped_pressures) != 4
        or len(final_window_supported) != 4
        or not all(final_window_supported)
    ):
        return "insufficient_support_or_evidence"
    if (
        clipped_pressure > 0.0
        and unclipped_pressure > 0.0
        and all(value > 0.0 for value in final_window_unclipped_pressures)
    ):
        return "take_pressure_persists_on_supported_unclipped_rows"
    if clipped_pressure > 0.0 and unclipped_pressure <= 0.0:
        return "take_pressure_concentrated_in_clipped_rows"
    return "take_pressure_not_consistently_aligned"


def _advantage_sign(value: float) -> str:
    if value > 0.0:
        return "positive"
    if value < 0.0:
        return "negative"
    return "zero"


def _floor_band(effective_floor: int) -> str:
    if effective_floor < 17:
        return "<17"
    if effective_floor < 34:
        return "17..33"
    return ">=34"


def _ordinal_band(ordinal: int) -> str:
    if ordinal == 0:
        return "first"
    if ordinal == 1:
        return "second"
    return "later"


class Summary:
    def __init__(self) -> None:
        self.count = 0
        self.clipping = Counter()
        self.selected = Counter()
        self.greedy = Counter()
        self.raw_returns: list[float] = []
        self.predictions: list[float] = []
        self.residual_squares: list[float] = []
        self.advantages: list[float] = []
        self.pressures: list[float] = []

    def add(
        self,
        row: Mapping[str, Any],
        *,
        clipping: str,
        pressure: float | None,
    ) -> None:
        self.count += 1
        self.clipping[clipping] += 1
        diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
        selected = diagnostic.get("selected_family")
        if isinstance(selected, str):
            self.selected[selected] += 1
        greedy = _sequence(
            diagnostic.get("raw_score_max_family_ids"), "greedy families"
        )
        self.greedy[greedy[0] if len(greedy) == 1 else "tie"] += 1
        raw_return = _finite(row.get("raw_return"), "raw return")
        prediction = _finite(row.get("baseline_prediction"), "prediction")
        advantage = _finite(row.get("advantage"), "advantage")
        self.raw_returns.append(raw_return)
        self.predictions.append(prediction)
        self.residual_squares.append((raw_return - prediction) ** 2)
        self.advantages.append(advantage)
        if pressure is not None:
            self.pressures.append(pressure)

    def result(self) -> dict[str, Any]:
        count = self.count
        return {
            "advantage_mean": math.fsum(self.advantages) / count,
            "advantage_signs": dict(
                sorted(Counter(_advantage_sign(v) for v in self.advantages).items())
            ),
            "clipping": dict(sorted(self.clipping.items())),
            "clipping_rates": {
                label: rows / count for label, rows in sorted(self.clipping.items())
            },
            "count": count,
            "direct_take_pressure_sum": (
                math.fsum(self.pressures) if self.pressures else None
            ),
            "greedy_families": dict(sorted(self.greedy.items())),
            "prediction_mean": math.fsum(self.predictions) / count,
            "raw_return_mean": math.fsum(self.raw_returns) / count,
            "residual_rmse": math.sqrt(math.fsum(self.residual_squares) / count),
            "selected_families": dict(sorted(self.selected.items())),
        }


class Contrast:
    def __init__(self) -> None:
        self.sides = {
            "clipped_high": Counter(),
            "clipped_low": Counter(),
            "unclipped": Counter(),
        }
        self.pressures = {
            "clipped_high": [],
            "clipped_low": [],
            "unclipped": [],
        }
        self.total = 0

    def add(self, clipping: str, selected: str, pressure: float) -> None:
        if clipping not in self.sides:
            raise AuditError(f"unknown clipping status: {clipping}")
        self.total += 1
        self.sides[clipping][selected] += 1
        self.pressures[clipping].append(pressure)

    def result(self, *, require_clipping_contrast: bool = True) -> dict[str, Any]:
        clipped_low = sum(self.sides["clipped_low"].values())
        clipped_high = sum(self.sides["clipped_high"].values())
        clipped = clipped_low + clipped_high
        unclipped = sum(self.sides["unclipped"].values())
        selected_take = sum(side.get("take", 0) for side in self.sides.values())
        selected_skip = sum(side.get("skip", 0) for side in self.sides.values())
        return {
            "clipped": {
                "count": clipped,
                "direct_take_pressure_sum": math.fsum(
                    self.pressures["clipped_low"]
                    + self.pressures["clipped_high"]
                ),
                "selected_families": dict(
                    sorted(
                        (
                            self.sides["clipped_low"]
                            + self.sides["clipped_high"]
                        ).items()
                    )
                ),
            },
            "clipped_high": {
                "count": clipped_high,
                "direct_take_pressure_sum": math.fsum(
                    self.pressures["clipped_high"]
                ),
                "selected_families": dict(
                    sorted(self.sides["clipped_high"].items())
                ),
            },
            "clipped_low": {
                "count": clipped_low,
                "direct_take_pressure_sum": math.fsum(
                    self.pressures["clipped_low"]
                ),
                "selected_families": dict(sorted(self.sides["clipped_low"].items())),
            },
            "support": support_status(
                total=self.total,
                clipped=clipped,
                unclipped=unclipped,
                selected_take=selected_take,
                selected_skip=selected_skip,
                require_clipping_contrast=require_clipping_contrast,
                require_take_skip=True,
            ),
            "total": self.total,
            "unclipped": {
                "count": unclipped,
                "direct_take_pressure_sum": math.fsum(self.pressures["unclipped"]),
                "selected_families": dict(sorted(self.sides["unclipped"].items())),
            },
        }


def summarize_final_window(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    eligible: list[Mapping[str, Any]] = []
    for raw in rows:
        row = _mapping(raw, "final-window row")
        diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
        chunk_index = _integer(row.get("chunk_index"), "chunk index")
        if (
            4 <= chunk_index <= 7
            and row.get("category") == "card_reward"
            and diagnostic.get("multi_family") is True
        ):
            eligible.append(row)
    greedy = Counter()
    exceptions: list[dict[str, Any]] = []
    for row in eligible:
        diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
        families = list(
            _sequence(diagnostic.get("raw_score_max_family_ids"), "greedy families")
        )
        family = families[0] if len(families) == 1 else "tie"
        greedy[family] += 1
        if family != "take":
            exceptions.append(
                {
                    "advantage": _finite(row.get("advantage"), "advantage"),
                    "chunk_index": _integer(row.get("chunk_index"), "chunk index"),
                    "decision_id": diagnostic.get("decision_id"),
                    "decision_index": _integer(
                        row.get("decision_index"), "decision index"
                    ),
                    "greedy_family": family,
                    "seed": _integer(row.get("seed"), "seed"),
                    "selected_family": diagnostic.get("selected_family"),
                    "trajectory_id": row.get("trajectory_id"),
                }
            )
    return {
        "greedy_families": dict(sorted(greedy.items())),
        "multi_family_decisions": len(eligible),
        "non_take_exceptions": exceptions,
        "registered_stop": len(greedy) == 1 and bool(eligible),
        "window_chunk_indices": [4, 5, 6, 7],
    }


def _reconcile_scalar_components(evidence: Mapping[str, Any]) -> dict[str, float]:
    rows = list(_sequence(evidence.get("decisions"), "decisions"))
    count = len(rows)
    calculated = {
        "card_reward_conditional_policy": math.fsum(
            -_finite(row["advantage"], "advantage")
            * _finite(row["policy_terms"]["selected_conditional_log_probability"], "log probability")
            for row in rows
            if row["category"] == "card_reward"
        )
        / count,
        "card_reward_family_policy": math.fsum(
            -_finite(row["advantage"], "advantage")
            * _finite(row["policy_terms"]["selected_family_log_probability"], "log probability")
            for row in rows
            if row["category"] == "card_reward"
        )
        / count,
        "conditional_entropy_regularizer": -CONDITIONAL_ENTROPY_COEFFICIENT
        * math.fsum(
            _finite(row["policy_terms"]["conditional_entropy"], "conditional entropy")
            for row in rows
        )
        / count,
        "family_entropy_regularizer": -FAMILY_ENTROPY_COEFFICIENT
        * math.fsum(
            _finite(row["policy_terms"]["family_entropy"], "family entropy")
            for row in rows
        )
        / count,
        "other_policy": math.fsum(
            -_finite(row["advantage"], "advantage")
            * _finite(row["policy_terms"]["selected_joint_log_probability"], "log probability")
            for row in rows
            if row["category"] != "card_reward"
        )
        / count,
    }
    stored = _mapping(
        _mapping(evidence.get("gradients"), "gradients").get("scalar_components"),
        "scalar components",
    )
    for name, value in calculated.items():
        if not math.isclose(
            value,
            _finite(stored.get(name), f"stored {name}"),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise AuditError(f"scalar component mismatch: {name}")
    return calculated


def _read_bound_chunk(
    terminal_root: Path,
    checkpoint: Mapping[str, Any],
) -> dict[str, Any]:
    binding = _mapping(checkpoint.get("chunk_evidence"), "chunk evidence binding")
    relative = binding.get("path")
    if not isinstance(relative, str):
        raise AuditError("chunk evidence path is invalid")
    path = _regular_file(terminal_root / relative, relative)
    stored = path.read_bytes()
    if len(stored) > MAX_GZIP_STORED_BYTES:
        raise AuditError("chunk evidence exceeds stored bound")
    if (
        len(stored) != _integer(binding.get("stored_size_bytes"), "stored size")
        or _digest(stored) != _sha256(binding.get("stored_sha256"), "stored digest")
    ):
        raise AuditError("chunk stored binding mismatch")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as handle:
            canonical = handle.read(MAX_GZIP_UNCOMPRESSED_BYTES + 1)
    except (OSError, EOFError) as exc:
        raise AuditError("chunk evidence gzip is invalid") from exc
    if len(canonical) > MAX_GZIP_UNCOMPRESSED_BYTES:
        raise AuditError("chunk evidence exceeds canonical bound")
    if (
        len(canonical)
        != _integer(binding.get("uncompressed_size_bytes"), "canonical size")
        or _digest(canonical)
        != _sha256(binding.get("uncompressed_sha256"), "canonical digest")
    ):
        raise AuditError("chunk canonical binding mismatch")
    return verifier._parse_canonical_json(canonical, label=relative)


def _validate_snapshot(terminal_root: Path) -> dict[str, Any]:
    terminal_path = _regular_file(terminal_root / "terminal.json", "terminal")
    manifest_path = _regular_file(
        terminal_root / "artifact_manifest.json", "artifact manifest"
    )
    terminal_raw = terminal_path.read_bytes()
    manifest_raw = manifest_path.read_bytes()
    if _digest(terminal_raw) != EXPECTED_TERMINAL_FILE_SHA256:
        raise AuditError("terminal file binding mismatch")
    if _digest(manifest_raw) != EXPECTED_MANIFEST_FILE_SHA256:
        raise AuditError("manifest file binding mismatch")
    terminal = verifier._parse_canonical_json(terminal_raw, label="terminal")
    manifest = verifier._parse_canonical_json(manifest_raw, label="manifest")
    if (
        terminal.get("identity") != EXPECTED_IDENTITY
        or terminal.get("terminal_sha256") != EXPECTED_TERMINAL_SHA256
        or terminal.get("verdict") != EXPECTED_VERDICT
        or manifest.get("identity") != EXPECTED_IDENTITY
        or manifest.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256
        or manifest.get("terminal_sha256") != EXPECTED_TERMINAL_SHA256
    ):
        raise AuditError("terminal or manifest identity mismatch")
    inventory = _mapping(manifest.get("artifact_inventory"), "artifact inventory")
    rows = list(_sequence(inventory.get("artifacts"), "artifact rows"))
    expected_files = {"artifact_manifest.json"}
    for raw_row in rows:
        row = _mapping(raw_row, "artifact row")
        relative = row.get("path")
        if not isinstance(relative, str):
            raise AuditError("artifact path is invalid")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise AuditError("artifact path escapes terminal root")
        expected_files.add(relative)
        path = _regular_file(terminal_root / Path(*pure.parts), relative)
        payload = path.read_bytes()
        if (
            len(payload) != _integer(row.get("stored_size_bytes"), "artifact size")
            or _digest(payload) != _sha256(row.get("stored_sha256"), "artifact digest")
        ):
            raise AuditError(f"artifact binding mismatch: {relative}")
    observed_files: set[str] = set()
    for path in terminal_root.rglob("*"):
        relative = path.relative_to(terminal_root).as_posix()
        if relative == ".execution.lease" or path.is_dir():
            continue
        _regular_file(path, relative)
        observed_files.add(relative)
    if observed_files != expected_files:
        raise AuditError("terminal snapshot inventory mismatch")
    return {"manifest": manifest, "terminal": terminal}


def _add_dimension(
    dimensions: dict[str, dict[str, Summary]],
    dimension: str,
    label: str,
    row: Mapping[str, Any],
    *,
    clipping: str,
    pressure: float | None,
) -> None:
    dimensions.setdefault(dimension, {}).setdefault(label, Summary()).add(
        row, clipping=clipping, pressure=pressure
    )


def _add_contrast(
    contrasts: dict[str, dict[str, Contrast]],
    dimension: str,
    label: str,
    *,
    clipping: str,
    selected: str,
    pressure: float,
) -> None:
    contrasts.setdefault(dimension, {}).setdefault(label, Contrast()).add(
        clipping, selected, pressure
    )


def _analyze_chunks(terminal_root: Path) -> dict[str, Any]:
    dimensions: dict[str, dict[str, Summary]] = {}
    contrasts: dict[str, dict[str, Contrast]] = {}
    chunk_results: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    total_trajectories = 0
    total_decisions = 0
    victories = 0

    for checkpoint_number in range(1, 9):
        checkpoint_path = _regular_file(
            terminal_root / "checkpoints" / f"checkpoint_{checkpoint_number:04d}.json",
            f"checkpoint {checkpoint_number}",
        )
        checkpoint = verifier._parse_canonical_json(
            checkpoint_path.read_bytes(), label=f"checkpoint {checkpoint_number}"
        )
        document = _read_bound_chunk(terminal_root, checkpoint)
        evidence = _mapping(document.get("evidence"), "chunk evidence")
        chunk_index = _integer(evidence.get("chunk_index"), "chunk index")
        if chunk_index != checkpoint_number - 1:
            raise AuditError("chunk order mismatch")
        rows = [
            _mapping(row, f"chunk {chunk_index} decision")
            for row in _sequence(evidence.get("decisions"), "decisions")
        ]
        baseline = _mapping(evidence.get("baseline"), "baseline")
        folds = {
            str(key): list(_sequence(value, f"{key} trajectories"))
            for key, value in _mapping(
                baseline.get("fold_trajectories"), "fold trajectories"
            ).items()
        }
        models = {
            str(model["fold_id"]): _mapping(model, "baseline model")
            for model in _sequence(baseline.get("models"), "baseline models")
        }
        validate_fold_rows(
            rows,
            folds,
            models,
            expected_held_out=16,
            expected_fit=48,
        )
        scalar_components = _reconcile_scalar_components(evidence)
        total_chunk_decisions = len(rows)
        trajectories = {str(row["trajectory_id"]) for row in rows}
        if len(trajectories) != 64:
            raise AuditError("chunk trajectory count mismatch")
        total_trajectories += len(trajectories)
        total_decisions += total_chunk_decisions
        floor_units: dict[str, int] = defaultdict(int)
        card_ordinals: dict[str, int] = defaultdict(int)
        chunk_summary = Summary()

        for row in rows:
            trajectory_id = str(row["trajectory_id"])
            clipping = validate_baseline_row(row, str(row.get("decision_id")))
            diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
            category = str(row.get("category"))
            selected = str(diagnostic.get("selected_family"))
            advantage = _finite(row.get("advantage"), "advantage")
            effective_floor = floor_units[trajectory_id]
            ordinal = card_ordinals[trajectory_id]
            pressure: float | None = None
            if (
                category == "card_reward"
                and diagnostic.get("multi_family") is True
                and "take"
                in _mapping(
                    diagnostic.get("family_probabilities"), "family probabilities"
                )
            ):
                pressure = direct_take_pressure(
                    row, total_chunk_decisions=total_chunk_decisions
                )["combined"]
                labels = {
                    "advantage_sign": _advantage_sign(advantage),
                    "chunk": str(chunk_index),
                    "effective_floor": _floor_band(effective_floor),
                    "fold": str(row.get("fold_id")),
                    "ordinal": _ordinal_band(ordinal),
                }
                for dimension, label in labels.items():
                    _add_contrast(
                        contrasts,
                        dimension,
                        label,
                        clipping=clipping,
                        selected=selected,
                        pressure=pressure,
                    )
                _add_contrast(
                    contrasts,
                    "global",
                    "all",
                    clipping=clipping,
                    selected=selected,
                    pressure=pressure,
                )
                card_ordinals[trajectory_id] += 1
                if chunk_index >= 4:
                    final_rows.append({"chunk_index": chunk_index, **dict(row)})

            dimension_labels = {
                "advantage_sign": _advantage_sign(advantage),
                "category": category,
                "chunk": str(chunk_index),
                "clipping_status": clipping,
                "effective_floor": _floor_band(effective_floor),
                "fold": str(row.get("fold_id")),
                "selected_family": f"{category}:{selected}",
            }
            if category == "card_reward":
                dimension_labels["card_reward_ordinal"] = _ordinal_band(ordinal)
            for dimension, label in dimension_labels.items():
                _add_dimension(
                    dimensions,
                    dimension,
                    label,
                    row,
                    clipping=clipping,
                    pressure=pressure,
                )
            chunk_summary.add(row, clipping=clipping, pressure=pressure)

            formal_reward = _mapping(
                diagnostic.get("formal_reward"), "formal reward"
            )
            floor_increment = _finite(
                formal_reward.get("floor_progress"), "floor progress"
            ) * 57.0
            rounded = round(floor_increment)
            if not math.isclose(
                floor_increment, rounded, rel_tol=0.0, abs_tol=1e-12
            ):
                raise AuditError("floor progress is not an exact floor unit")
            floor_units[trajectory_id] += int(rounded)
            victories += int(
                _integer(formal_reward.get("terminal_victory"), "terminal victory")
            )

        gradient_comparison = dict(
            _mapping(
                _mapping(evidence.get("gradients"), "gradients").get(
                    "gradient_comparison"
                ),
                "gradient comparison",
            )
        )
        chunk_results.append(
            {
                "chunk_index": chunk_index,
                "gradient_comparison": gradient_comparison,
                "scalar_components": scalar_components,
                "summary": chunk_summary.result(),
                "trajectories": 64,
            }
        )

    dimension_results = {
        dimension: [
            {"label": label, **summary.result()}
            for label, summary in sorted(groups.items())
        ]
        for dimension, groups in sorted(dimensions.items())
    }
    contrast_results = {
        dimension: [
            {"label": label, **contrast.result()}
            for label, contrast in sorted(groups.items())
        ]
        for dimension, groups in sorted(contrasts.items())
    }
    global_contrast = contrasts["global"]["all"].result()
    final_pressures: list[float] = []
    final_supported: list[bool] = []
    for chunk_index in range(4, 8):
        contrast = contrasts["chunk"][str(chunk_index)]
        side = contrast.sides["unclipped"]
        final_pressures.append(math.fsum(contrast.pressures["unclipped"]))
        final_supported.append(
            support_status(
                total=sum(side.values()),
                clipped=0,
                unclipped=0,
                selected_take=side.get("take", 0),
                selected_skip=side.get("skip", 0),
                require_clipping_contrast=False,
                require_take_skip=True,
            )
            == "supported"
        )
    verdict = classify_verdict(
        global_supported=global_contrast["support"] == "supported",
        clipped_pressure=global_contrast["clipped"][
            "direct_take_pressure_sum"
        ],
        unclipped_pressure=global_contrast["unclipped"][
            "direct_take_pressure_sum"
        ],
        final_window_unclipped_pressures=final_pressures,
        final_window_supported=final_supported,
    )
    final_window = summarize_final_window(final_rows)
    if (
        final_window["multi_family_decisions"] != 1774
        or final_window["greedy_families"] != {"bowl": 1, "take": 1773}
        or final_window["registered_stop"] is not False
    ):
        raise AuditError("registered final-window near saturation mismatch")
    return {
        "card_reward_support_contrasts": contrast_results,
        "chunk_results": chunk_results,
        "dimensions": dimension_results,
        "execution_counts": {
            "chunks": len(chunk_results),
            "decisions": total_decisions,
            "trajectories": total_trajectories,
            "victories": victories,
        },
        "final_window": final_window,
        "verdict": verdict,
        "verdict_inputs": {
            "clipped_pressure": global_contrast["clipped"][
                "direct_take_pressure_sum"
            ],
            "final_window_supported": final_supported,
            "final_window_unclipped_pressures": final_pressures,
            "global_support": global_contrast["support"],
            "unclipped_pressure": global_contrast["unclipped"][
                "direct_take_pressure_sum"
            ],
        },
    }


def build_repository_audit(
    repo_root: Path | str, *, source_commit: str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    source = verify_pushed_source(root, source_commit)
    terminal_root = (root / DEFAULT_TERMINAL_ROOT).resolve()
    postmortem_path = _regular_file(
        root / DEFAULT_POSTMORTEM_PATH, "r2 postmortem"
    )
    postmortem_raw = postmortem_path.read_bytes()
    if _digest(postmortem_raw) != EXPECTED_POSTMORTEM_SHA256:
        raise AuditError("r2 postmortem binding mismatch")
    postmortem = parse_json_bytes(postmortem_raw, "r2 postmortem")
    if (
        postmortem.get("identity") != EXPECTED_IDENTITY
        or _mapping(postmortem.get("classification"), "classification").get(
            "verdict"
        )
        != EXPECTED_VERDICT
    ):
        raise AuditError("r2 postmortem identity mismatch")

    try:
        verification = verifier.verify_terminal_bundle(terminal_root, repo_root=root)
    except (OSError, verifier.VerifierError) as exc:
        raise AuditError(f"independent terminal verification failed: {exc}") from exc
    validate_verifier_result(verification)

    with hold_inactive_lease(terminal_root / ".execution.lease"):
        _validate_snapshot(terminal_root)
        analysis = _analyze_chunks(terminal_root)

    forbidden = forbidden_loaded_modules()
    if forbidden:
        raise AuditError(f"forbidden modules loaded: {forbidden}")
    return {
        "authority": audit_authority(),
        "evidence": analysis,
        "identity": EXPECTED_IDENTITY,
        "input_bindings": {
            "artifact_manifest": {
                "path": f"{DEFAULT_TERMINAL_ROOT}/artifact_manifest.json",
                "sha256": EXPECTED_MANIFEST_FILE_SHA256,
            },
            "postmortem": {
                "path": DEFAULT_POSTMORTEM_PATH,
                "sha256": EXPECTED_POSTMORTEM_SHA256,
                "size_bytes": len(postmortem_raw),
            },
            "terminal": {
                "path": f"{DEFAULT_TERMINAL_ROOT}/terminal.json",
                "sha256": EXPECTED_TERMINAL_FILE_SHA256,
            },
        },
        "limitations": list(LIMITATIONS),
        "schema_version": AUDIT_SCHEMA_VERSION,
        "scope": {
            "artifact_mutation": False,
            "environment_construction": False,
            "evaluation": False,
            "model_loading": False,
            "native_loading": False,
            "new_seed_access": False,
            "source_only": True,
            "training_or_replay": False,
        },
        "source": source,
        "terminal_verification": {
            "checkpoint_count": verification["checkpoint_count"],
            "completed_chunk_indices": verification["completed_chunk_indices"],
            "manifest_sha256": verification["manifest_sha256"],
            "resource_use": verification["resource_use"],
            "terminal_sha256": verification["terminal_sha256"],
            "verdict": verification["verdict"],
        },
        "verdict": analysis["verdict"],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    verdict = str(report.get("verdict", "unknown"))
    evidence = report.get("evidence")
    if not isinstance(evidence, Mapping):
        return (
            "# Cross-Fitted Baseline Support Audit\n\n"
            f"Verdict: `{verdict}`\n\n"
            "All downstream authority remains false.\n"
        )
    counts = _mapping(evidence.get("execution_counts"), "execution counts")
    inputs = _mapping(evidence.get("verdict_inputs"), "verdict inputs")
    final = _mapping(evidence.get("final_window"), "final window")
    dimensions = _mapping(evidence.get("dimensions"), "dimensions")
    clipping_rows = {
        str(row["label"]): row
        for row in _sequence(dimensions.get("clipping_status"), "clipping rows")
    }
    low = _mapping(clipping_rows.get("clipped_low"), "clipped low")
    unclipped = _mapping(clipping_rows.get("unclipped"), "unclipped")
    lines = [
        "# Cross-Fitted Baseline Support Audit",
        "",
        "## Decision",
        "",
        f"The bounded descriptive verdict is `{verdict}`.",
        "It authorizes no training, evaluation, OPE, model loading, gameplay,",
        "qualification, promotion, policy-quality, causal, or formal-RL claim.",
        "",
        "## Verified Evidence",
        "",
        f"- Trajectories: {counts['trajectories']}",
        f"- Decisions: {counts['decisions']}",
        f"- Chunks/checkpoints: {counts['chunks']}",
        f"- Victories: {counts['victories']}",
        "- Terminal and manifest were independently verified under the inactive lease.",
        "",
        "## Baseline Support",
        "",
        "| Support | Rows | Prediction mean | Residual RMSE | Advantage mean |",
        "| --- | ---: | ---: | ---: | ---: |",
        (
            "| Clipped low | {count} | {prediction_mean:.9f} | "
            "{residual_rmse:.9f} | {advantage_mean:.9f} |"
        ).format(**low),
        (
            "| Unclipped | {count} | {prediction_mean:.9f} | "
            "{residual_rmse:.9f} | {advantage_mean:.9f} |"
        ).format(**unclipped),
        "",
        "## Card-Reward Attribution",
        "",
        f"- Global clipping contrast: `{inputs['global_support']}`",
        f"- Clipped direct take pressure: {inputs['clipped_pressure']:.12g}",
        f"- Unclipped direct take pressure: {inputs['unclipped_pressure']:.12g}",
        "- Final-window unclipped pressures: "
        + ", ".join(f"{value:.12g}" for value in inputs["final_window_unclipped_pressures"]),
        "",
        "The final window contains "
        f"{final['multi_family_decisions']} multi-family card-reward decisions: "
        f"{final['greedy_families']}. The exact registered saturation predicate "
        f"remains `{str(final['registered_stop']).lower()}`; the single exception "
        "does not establish robust greedy diversity.",
        "",
        "## Next Gate",
        "",
        "Use this result only for a separately reviewed source-level mechanism",
        "proposal. Do not start another empirical run from this audit alone.",
        "",
    ]
    return "\n".join(lines)


def _atomic_write_pair(
    json_path: Path,
    json_payload: bytes,
    markdown_path: Path,
    markdown_payload: bytes,
) -> None:
    if json_path.exists() or markdown_path.exists():
        raise AuditError("report output already exists")
    staged: list[tuple[Path, Path]] = []
    try:
        for target, payload in (
            (json_path, json_payload),
            (markdown_path, markdown_payload),
        ):
            with tempfile.NamedTemporaryFile(
                dir=target.parent, prefix=f".{target.name}.", delete=False
            ) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                staged.append((Path(handle.name), target))
        for temporary, target in staged:
            os.replace(temporary, target)
    except Exception:
        for temporary, target in staged:
            if temporary.exists():
                temporary.unlink()
            if target.exists():
                target.unlink()
        raise


def publish_reports(
    report: Mapping[str, Any], output_dir: Path | str
) -> tuple[Path, Path]:
    value = dict(report)
    if value.get("schema_version") != AUDIT_SCHEMA_VERSION:
        raise AuditError("report schema mismatch")
    if value.get("authority") != audit_authority():
        raise AuditError("report authority must be all false")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / DEFAULT_JSON_NAME
    markdown_path = root / DEFAULT_MARKDOWN_NAME
    _atomic_write_pair(
        json_path,
        canonical_json_bytes(value),
        markdown_path,
        render_markdown(value).encode("utf-8"),
    )
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit sealed cross-fitted baseline support"
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_repository_audit(
            args.repo_root, source_commit=args.source_commit
        )
        paths = publish_reports(report, args.output_dir)
    except (AuditError, OSError) as exc:
        sys.stderr.write(f"audit blocked: {exc}\n")
        return 1
    sys.stdout.write(
        json.dumps(
            {
                "json": str(paths[0]),
                "markdown": str(paths[1]),
                "status": "published",
                "verdict": report["verdict"],
            },
            sort_keys=True,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
