"""Source-only publication validator for card-acceptance stage authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any


MAX_INPUT_BYTES = 4 * 1024 * 1024
CONTROL_PATH = (
    Path(__file__).resolve().parent
    / "noncombat_card_acceptance_empirical_successor_experiment.py"
)
CONTROL_SHA256 = (
    "25b436ffdcb322e8ed2285b8d073f4e5aa98a274ef9cef34ceeb233040045527"
)
CONTROL_SIZE_BYTES = 182511


class PublicationValidationError(RuntimeError):
    """Raised when publication inputs are missing or malformed."""


def _read_at_most(
    path: Path | str, label: str, *, maximum_bytes: int
) -> bytes:
    candidate = Path(path).resolve()
    try:
        with candidate.open("rb") as handle:
            payload = handle.read(maximum_bytes + 1)
    except OSError as exc:
        raise PublicationValidationError(f"{label} cannot be read") from exc
    if not payload or len(payload) > maximum_bytes:
        raise PublicationValidationError(f"{label} byte size is invalid")
    return payload


def _load_control() -> ModuleType:
    payload = _read_at_most(
        CONTROL_PATH,
        "bound control module",
        maximum_bytes=CONTROL_SIZE_BYTES,
    )
    if (
        len(payload) != CONTROL_SIZE_BYTES
        or hashlib.sha256(payload).hexdigest() != CONTROL_SHA256
    ):
        raise PublicationValidationError("bound control module identity differs")
    module_name = "_card_acceptance_authorization_publication_control"
    module = ModuleType(module_name)
    module.__file__ = str(CONTROL_PATH)
    module.__package__ = ""
    sys.modules[module_name] = module
    try:
        exec(compile(payload, str(CONTROL_PATH), "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PublicationValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise PublicationValidationError(f"non-finite JSON constant: {value}")


def _read_bounded_bytes(path: Path | str, label: str) -> bytes:
    return _read_at_most(path, label, maximum_bytes=MAX_INPUT_BYTES)


def _read_json_mapping(path: Path | str, label: str) -> dict[str, Any]:
    payload = _read_bounded_bytes(path, label)
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except PublicationValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationValidationError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise PublicationValidationError(f"{label} must be a JSON object")
    return value


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def validate_stage_authorization_publication(
    *,
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval: Mapping[str, Any],
    request_review_bytes: bytes,
) -> dict[str, Any]:
    """Validate the complete request-review-approval-authorization chain."""
    control = _load_control()
    normalized_request = control.validate_stage_request(request)
    normalized_authorization = control.validate_stage_authorization(
        authorization, normalized_request
    )
    if (
        type(request_review_bytes) is not bytes
        or not request_review_bytes
        or len(request_review_bytes) > MAX_INPUT_BYTES
    ):
        raise PublicationValidationError("request review bytes are invalid")
    request_review_sha256 = hashlib.sha256(request_review_bytes).hexdigest()
    approval_mode = approval.get("approval_mode")
    if approval_mode == "standing-delegation":
        normalized_approval = control.validate_delegated_approval(
            approval, normalized_request
        )
    elif approval_mode == "external-human-approval":
        normalized_approval = control.validate_external_human_approval(
            approval, normalized_request
        )
    else:
        raise PublicationValidationError("approval record mode is invalid")
    if (
        normalized_approval["request_review_sha256"]
        != request_review_sha256
        or normalized_authorization["request_review_sha256"]
        != request_review_sha256
    ):
        raise PublicationValidationError("request review binding mismatch")
    if (
        normalized_authorization["approval_record_sha256"]
        != normalized_approval["approval_sha256"]
    ):
        raise PublicationValidationError("authorization approval binding mismatch")
    return {
        "approval_mode": approval_mode,
        "approval_sha256": normalized_approval["approval_sha256"],
        "authorization_sha256": normalized_authorization[
            "authorization_sha256"
        ],
        "request_review_sha256": request_review_sha256,
        "request_sha256": normalized_request["request_sha256"],
        "stage": normalized_request["stage"],
        "validated": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a complete card-acceptance authority publication"
    )
    parser.add_argument("--request", required=True)
    parser.add_argument("--request-review", required=True)
    parser.add_argument("--approval", required=True)
    parser.add_argument("--authorization", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = validate_stage_authorization_publication(
        request=_read_json_mapping(args.request, "stage request"),
        authorization=_read_json_mapping(
            args.authorization, "stage authorization"
        ),
        approval=_read_json_mapping(args.approval, "approval record"),
        request_review_bytes=_read_bounded_bytes(
            args.request_review, "request review"
        ),
    )
    print(_canonical_json_bytes(output).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
