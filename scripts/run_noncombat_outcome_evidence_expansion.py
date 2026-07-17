#!/usr/bin/env python3
"""Operate the fixed, no-training non-combat outcome-evidence study."""

from __future__ import annotations

import base64
import hashlib
import os
import sys

QUALIFICATION_RUNNER_SHA256_ENV = (
    "STS_OUTCOME_EVIDENCE_QUALIFICATION_RUNNER_SHA256"
)
QUALIFICATION_RUNNER_RELATIVE_PATH = (
    "scripts/run_noncombat_outcome_evidence_expansion.py"
)
_QUALIFICATION_TRUSTED_LAUNCHER_PAYLOAD = (
    "import hashlib,os,stat,sys\n"
    "from pathlib import Path\n"
    "sys.stderr=open(os.devnull,'w')\n"
    "def reject(message):\n"
    " raise SystemExit(2)\n"
    "if len(sys.argv)<3: reject('arguments are invalid')\n"
    "runner=Path(sys.argv[1])\n"
    "expected=sys.argv[2]\n"
    "if (not runner.is_absolute()) or str(runner).startswith('\\\\\\\\'): "
    "reject('runner path must be local absolute')\n"
    "if any(':' in part for part in runner.parts[1:]): "
    "reject('runner path contains an alternate data stream')\n"
    "if any(part.endswith(('.', ' ')) for part in runner.parts[1:]): "
    "reject('runner path contains a Win32 alias component')\n"
    "runner=Path(os.path.abspath(str(runner)))\n"
    "if len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected): "
    "reject('runner SHA-256 is invalid')\n"
    "current=Path(runner.anchor)\n"
    "for part in runner.parts[1:]:\n"
    " current/=part\n"
    " try: metadata=current.lstat()\n"
    " except OSError as exc: reject('cannot inspect runner path: '+str(exc))\n"
    " attributes=getattr(metadata,'st_file_attributes',0)\n"
    " reparse=getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0)\n"
    " if stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse): "
    "reject('runner path contains a link or reparse point')\n"
    "if not stat.S_ISREG(runner.lstat().st_mode): "
    "reject('runner is not a regular file')\n"
    "try: source=runner.read_bytes()\n"
    "except OSError as exc: reject('cannot read runner bytes: '+str(exc))\n"
    "if hashlib.sha256(source).hexdigest()!=expected: "
    "reject('runner SHA-256 mismatch')\n"
    f"os.environ[{QUALIFICATION_RUNNER_SHA256_ENV!r}]=expected\n"
    "sys.argv=[str(runner),*sys.argv[3:]]\n"
    "scope={'__name__':'__main__','__file__':str(runner),"
    "'__package__':None,'__cached__':None,'__spec__':None,'__loader__':None}\n"
    "exec(compile(source,str(runner),'exec'),scope)\n"
)
_QUALIFICATION_TRUSTED_LAUNCHER_PAYLOAD_B64 = base64.b64encode(
    _QUALIFICATION_TRUSTED_LAUNCHER_PAYLOAD.encode("utf-8")
).decode("ascii")
QUALIFICATION_TRUSTED_LAUNCHER_CODE = (
    "exec(compile(__import__('base64').b64decode('"
    + _QUALIFICATION_TRUSTED_LAUNCHER_PAYLOAD_B64
    + "'),'<qualification-launcher>','exec'))"
)

_QUALIFICATION_CLI_REQUESTED = (
    len(sys.argv) > 1
    and sys.argv[1] == "qualify"
)


class _QualificationSilentStream:
    def __init__(self, stream):
        self._stream = stream

    @property
    def buffer(self):
        return self

    @property
    def encoding(self):
        return getattr(self._stream, "encoding", None)

    @property
    def errors(self):
        return getattr(self._stream, "errors", None)

    def fileno(self):
        return self._stream.fileno()

    def flush(self):
        return None

    def isatty(self):
        return False

    def write(self, value):
        try:
            return len(value)
        except TypeError:
            return 0


if __name__ == "__main__" and _QUALIFICATION_CLI_REQUESTED:
    sys.stdout = _QualificationSilentStream(sys.stdout)
    sys.stderr = _QualificationSilentStream(sys.stderr)

if _QUALIFICATION_CLI_REQUESTED:
    sys.dont_write_bytecode = True
    sys.pycache_prefix = os.path.join(
        os.devnull,
        "sts-qualification-pycache",
    )

if (
    __name__ == "__main__"
    and _QUALIFICATION_CLI_REQUESTED
    and (not sys.flags.isolated or not sys.flags.no_site)
):
    raise SystemExit(2)


def _qualification_require_trusted_launcher() -> None:
    anchor = os.environ.get(QUALIFICATION_RUNNER_SHA256_ENV)
    original_arguments = tuple(sys.orig_argv)
    runner_path = os.path.abspath(__file__)
    valid_shape = (
        isinstance(anchor, str)
        and len(original_arguments) >= 8
        and original_arguments[1:5]
        == ("-I", "-S", "-c", QUALIFICATION_TRUSTED_LAUNCHER_CODE)
        and os.path.abspath(original_arguments[5]) == runner_path
        and original_arguments[6] == anchor
        and original_arguments[7:] == tuple(sys.argv[1:])
    )
    if not valid_shape:
        raise SystemExit(2)
    try:
        with open(runner_path, "rb") as runner_stream:
            runner_bytes = runner_stream.read()
    except OSError as exc:
        raise SystemExit(2) from exc
    if hashlib.sha256(runner_bytes).hexdigest() != anchor:
        raise SystemExit(2)


if (
    __name__ == "__main__"
    and _QUALIFICATION_CLI_REQUESTED
):
    _qualification_require_trusted_launcher()

import argparse
import importlib.machinery
import json
import stat
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _qualification_install_source_only_repo_imports(repo_root: Path) -> None:
    lexical_root = os.path.normcase(os.path.abspath(repo_root))

    def is_repo_path(path_value: object) -> bool:
        try:
            lexical_path = os.path.normcase(
                os.path.abspath(os.fspath(path_value))
            )
            return os.path.commonpath((lexical_root, lexical_path)) == lexical_root
        except (OSError, TypeError, ValueError):
            return False

    class NoFollowSourceLoader(importlib.machinery.SourceFileLoader):
        def get_data(self, path_value: str) -> bytes:
            lexical_path = os.path.abspath(path_value)
            if not is_repo_path(lexical_path):
                raise OSError(
                    "qualification repository loader refuses bytecode cache"
                )
            current = Path(lexical_path).anchor
            current_path = Path(current)
            for part in Path(lexical_path).parts[1:]:
                current_path /= part
                metadata = current_path.lstat()
                file_attributes = getattr(metadata, "st_file_attributes", 0)
                reparse_flag = getattr(
                    stat,
                    "FILE_ATTRIBUTE_REPARSE_POINT",
                    0,
                )
                if stat.S_ISLNK(metadata.st_mode) or bool(
                    file_attributes & reparse_flag
                ):
                    raise ImportError(
                        "qualification repository source contains a symbolic "
                        f"link or reparse point: {current_path}"
                    )
            if not stat.S_ISREG(current_path.lstat().st_mode):
                raise ImportError(
                    "qualification repository source is not a regular file: "
                    f"{current_path}"
                )
            return super().get_data(lexical_path)

    def source_only_path_hook(path_value: str):
        if not is_repo_path(path_value):
            raise ImportError
        return importlib.machinery.FileFinder(
            path_value,
            (
                NoFollowSourceLoader,
                importlib.machinery.SOURCE_SUFFIXES,
            ),
        )

    sys.path_hooks.insert(0, source_only_path_hook)
    for cached_path in tuple(sys.path_importer_cache):
        if is_repo_path(cached_path):
            sys.path_importer_cache.pop(cached_path, None)


if _QUALIFICATION_CLI_REQUESTED:
    _qualification_install_source_only_repo_imports(REPO_ROOT)


class _QualificationBootstrapError(RuntimeError):
    pass


_QUALIFICATION_BOOTSTRAP_GIT = Path(r"C:\Program Files\Git\cmd\git.exe")
_QUALIFICATION_INERT_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".tsv",
    ".txt",
}
def _qualification_bootstrap_is_link_or_reparse(metadata: os.stat_result) -> bool:
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(file_attributes & reparse_flag)


def _qualification_bootstrap_require_path(
    path_value: Path | str,
    label: str,
    *,
    expected_kind: str,
) -> Path:
    supplied_path = Path(os.fspath(path_value))
    supplied_components = (
        supplied_path.parts[1:] if supplied_path.anchor else supplied_path.parts
    )
    if any(":" in part for part in supplied_components):
        raise _QualificationBootstrapError(
            f"qualification bootstrap {label} contains an alternate data "
            "stream"
        )
    if any(part.endswith((".", " ")) for part in supplied_components):
        raise _QualificationBootstrapError(
            f"qualification bootstrap {label} contains a Win32 alias "
            "component"
        )
    lexical_path = Path(os.path.abspath(supplied_path))
    if lexical_path.drive.startswith("\\\\"):
        raise _QualificationBootstrapError(
            f"qualification bootstrap {label} must use a local drive"
        )
    current_path = Path(lexical_path.anchor)
    for part in lexical_path.parts[1:]:
        current_path /= part
        try:
            metadata = current_path.lstat()
        except OSError as exc:
            raise _QualificationBootstrapError(
                f"cannot inspect qualification bootstrap {label}: "
                f"{current_path}: {exc}"
            ) from exc
        if _qualification_bootstrap_is_link_or_reparse(metadata):
            raise _QualificationBootstrapError(
                f"qualification bootstrap {label} contains a symbolic link "
                f"or reparse point: {current_path}"
            )
    metadata = lexical_path.lstat()
    expected = (
        stat.S_ISDIR(metadata.st_mode)
        if expected_kind == "directory"
        else stat.S_ISREG(metadata.st_mode)
    )
    if not expected:
        raise _QualificationBootstrapError(
            f"qualification bootstrap {label} is not a regular {expected_kind}"
        )
    return lexical_path


def _qualification_bootstrap_entry_exists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise _QualificationBootstrapError(
            f"cannot inspect qualification bootstrap path: {path}: {exc}"
        ) from exc
    return True


def _qualification_bootstrap_walk(
    root: Path,
    *,
    skip_root_git: bool = False,
):
    pending = [root]
    while pending:
        current = _qualification_bootstrap_require_path(
            pending.pop(),
            "source directory",
            expected_kind="directory",
        )
        try:
            with os.scandir(current) as iterator:
                children = list(iterator)
        except OSError as exc:
            raise _QualificationBootstrapError(
                f"cannot traverse qualification bootstrap source: {current}: {exc}"
            ) from exc
        for child in children:
            if skip_root_git and current == root and child.name == ".git":
                continue
            try:
                metadata = child.stat(follow_symlinks=False)
            except OSError as exc:
                raise _QualificationBootstrapError(
                    "cannot inspect qualification bootstrap source entry: "
                    f"{child.path}: {exc}"
                ) from exc
            path = Path(child.path)
            if _qualification_bootstrap_is_link_or_reparse(metadata):
                raise _QualificationBootstrapError(
                    "qualification bootstrap source contains a symbolic link "
                    f"or reparse point: {path}"
                )
            yield path, metadata
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(path)


def _qualification_bootstrap_validate_git_metadata(repo_root: Path) -> Path:
    git_root = _qualification_bootstrap_require_path(
        repo_root / ".git",
        "Git metadata root",
        expected_kind="directory",
    )
    for _path, _metadata in _qualification_bootstrap_walk(git_root):
        pass
    for relative_path, label in (
        ("info/grafts", "grafts"),
        ("info/attributes", "info attributes"),
        ("commondir", "common directory"),
        ("objects/info/alternates", "object alternates"),
        ("objects/info/http-alternates", "HTTP object alternates"),
        ("refs/replace", "replacement refs"),
    ):
        if _qualification_bootstrap_entry_exists(git_root / relative_path):
            raise _QualificationBootstrapError(
                f"qualification bootstrap Git {label} are forbidden"
            )
    packed_refs_path = git_root / "packed-refs"
    if _qualification_bootstrap_entry_exists(packed_refs_path):
        packed_refs_path = _qualification_bootstrap_require_path(
            packed_refs_path,
            "packed refs",
            expected_kind="file",
        )
        try:
            packed_refs = packed_refs_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise _QualificationBootstrapError(
                f"cannot inspect qualification bootstrap packed refs: {exc}"
            ) from exc
        if any(
            row[-1].startswith("refs/replace/")
            for line in packed_refs.splitlines()
            if line and not line.startswith(("#", "^"))
            if len(row := line.split()) >= 2
        ):
            raise _QualificationBootstrapError(
                "qualification bootstrap Git replacement refs are forbidden"
            )
    forbidden_config_tokens = (
        "[include",
        "fsmonitor",
        "hookspath",
        "external=",
        "filter",
        "clean=",
        "process=",
        "attributesfile",
        "textconv",
        "sshcommand",
        "partialclone",
        "promisor",
        "[protocol",
        "protocol.ext.allow",
        "ext::",
    )
    for config_name in ("config", "config.worktree"):
        config_path = git_root / config_name
        if not _qualification_bootstrap_entry_exists(config_path):
            continue
        config_path = _qualification_bootstrap_require_path(
            config_path,
            config_name,
            expected_kind="file",
        )
        try:
            normalized_config = "".join(
                config_path.read_text(encoding="utf-8").casefold().split()
            )
        except (OSError, UnicodeError) as exc:
            raise _QualificationBootstrapError(
                f"cannot inspect qualification bootstrap Git config: {exc}"
            ) from exc
        if any(token in normalized_config for token in forbidden_config_tokens):
            raise _QualificationBootstrapError(
                "qualification bootstrap Git config contains an unsafe directive"
            )
    return git_root


def _qualification_bootstrap_git_environment(
    repo_root: Path,
    git_root: Path,
) -> dict[str, str]:
    environment = {
        key: value
        for key in ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP")
        if (value := os.environ.get(key))
    }
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_DIR": str(git_root),
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_WORK_TREE": str(repo_root),
            "LC_ALL": "C",
        }
    )
    return environment


def _qualification_bootstrap_git_output(
    repo_root: Path,
    git_root: Path,
    *arguments: str,
    binary: bool = False,
    input_bytes: bytes | None = None,
) -> str | bytes:
    git_executable = _qualification_bootstrap_require_path(
        _QUALIFICATION_BOOTSTRAP_GIT,
        "Git executable",
        expected_kind="file",
    )
    command = [
        str(git_executable),
        "--no-pager",
        "--no-replace-objects",
        "--no-lazy-fetch",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=NUL",
        "-c",
        "diff.external=",
        "-c",
        "color.ui=false",
        *arguments,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=False,
            env=_qualification_bootstrap_git_environment(repo_root, git_root),
            input=input_bytes,
            text=not binary,
            encoding=None if binary else "utf-8",
        )
    except OSError as exc:
        raise _QualificationBootstrapError(
            f"cannot inspect qualification bootstrap source: {exc}"
        ) from exc
    stderr = completed.stderr
    stderr_text = (
        stderr.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes)
        else str(stderr or "")
    ).strip()
    if completed.returncode != 0 or stderr_text:
        detail = stderr_text or f"exit code {completed.returncode}"
        raise _QualificationBootstrapError(
            "cannot inspect qualification bootstrap source: "
            f"git {' '.join(arguments)}: {detail}"
        )
    return completed.stdout


def _qualification_bootstrap_review_commit(
    arguments: Sequence[str],
) -> str:
    option = "--review-commit"
    values = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == option:
            index += 1
            if index >= len(arguments):
                raise _QualificationBootstrapError(
                    "qualification bootstrap review commit is missing"
                )
            values.append(arguments[index])
        elif argument.startswith(f"{option}="):
            values.append(argument.partition("=")[2])
        index += 1
    if len(values) != 1:
        raise _QualificationBootstrapError(
            "qualification bootstrap requires exactly one review commit"
        )
    review_commit = values[0]
    if (
        len(review_commit) != 40
        or any(character not in "0123456789abcdef" for character in review_commit)
    ):
        raise _QualificationBootstrapError(
            "qualification bootstrap review commit is invalid"
        )
    return review_commit


def _qualification_bootstrap_path_may_execute(relative_path: str) -> bool:
    return (
        Path(relative_path).suffix.casefold()
        not in _QUALIFICATION_INERT_SUFFIXES
    )


def _qualification_bootstrap_path_requires_reviewed_bytes(
    relative_path: str,
) -> bool:
    return _qualification_bootstrap_path_may_execute(relative_path)


def _qualification_bootstrap_validate_reviewed_source_bytes(
    repo_root: Path,
    git_root: Path,
    review_commit: str,
) -> None:
    tree_raw = _qualification_bootstrap_git_output(
        repo_root,
        git_root,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        review_commit,
        binary=True,
    )
    if not isinstance(tree_raw, bytes):
        raise _QualificationBootstrapError(
            "qualification bootstrap review tree is invalid"
        )
    try:
        tree_entries = []
        for row in tree_raw.split(b"\0"):
            if not row:
                continue
            metadata, separator, raw_path = row.partition(b"\t")
            fields = metadata.split(b" ")
            if not separator or len(fields) != 3:
                raise _QualificationBootstrapError(
                    "qualification bootstrap review tree row is invalid"
                )
            _mode, object_type, object_id = fields
            relative_path = raw_path.decode("utf-8")
            if object_type != b"blob" or len(object_id) != 40:
                raise _QualificationBootstrapError(
                    "qualification bootstrap reviewed source is not a Git blob: "
                    f"{relative_path}"
                )
            relative = Path(relative_path)
            if (
                relative.is_absolute()
                or relative.as_posix() != relative_path
                or any(part in {"", ".", ".."} for part in relative.parts)
            ):
                raise _QualificationBootstrapError(
                    "qualification bootstrap reviewed source path is invalid: "
                    f"{relative_path}"
                )
            tree_entries.append((relative_path, relative, object_id))

        tracked_paths = {relative_path for relative_path, _relative, _oid in tree_entries}
        for path, _metadata in _qualification_bootstrap_walk(
            repo_root,
            skip_root_git=True,
        ):
            if (
                path.name.casefold() == ".gitattributes"
                and path.relative_to(repo_root).as_posix() not in tracked_paths
            ):
                raise _QualificationBootstrapError(
                    "qualification bootstrap unreviewed worktree attributes "
                    "are forbidden"
                )

        allowed_attribute_tokens = {
            "-text",
            "eol=crlf",
            "eol=lf",
            "text",
            "whitespace=cr-at-eol",
        }
        for relative_path, relative, object_id in tree_entries:
            if not _qualification_bootstrap_path_requires_reviewed_bytes(
                relative_path
            ):
                continue
            source_path = _qualification_bootstrap_require_path(
                repo_root / relative,
                f"reviewed source {relative_path}",
                expected_kind="file",
            )
            try:
                source_bytes = source_path.read_bytes()
            except OSError as exc:
                raise _QualificationBootstrapError(
                    "cannot read qualification bootstrap reviewed source bytes: "
                    f"{relative_path}: {exc}"
                ) from exc
            if source_path.name.casefold() == ".gitattributes":
                raw_object_id = hashlib.sha1(
                    b"blob "
                    + str(len(source_bytes)).encode("ascii")
                    + b"\0"
                    + source_bytes
                ).hexdigest().encode("ascii")
                if raw_object_id != object_id:
                    raise _QualificationBootstrapError(
                        "qualification bootstrap reviewed source bytes changed: "
                        f"{relative_path}"
                    )
                try:
                    attribute_text = source_bytes.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise _QualificationBootstrapError(
                        "qualification bootstrap worktree attributes are not "
                        "UTF-8"
                    ) from exc
                for line in attribute_text.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    tokens = stripped.split()
                    if (
                        len(tokens) < 2
                        or tokens[0].casefold().startswith("[attr]")
                        or any(
                            token.casefold() not in allowed_attribute_tokens
                            for token in tokens[1:]
                        )
                    ):
                        raise _QualificationBootstrapError(
                            "qualification bootstrap worktree attributes contain "
                            "an unsafe directive"
                        )
                continue
            canonical_object_id = _qualification_bootstrap_git_output(
                repo_root,
                git_root,
                "-c",
                "core.autocrlf=true",
                "hash-object",
                f"--path={relative_path}",
                "--stdin",
                binary=True,
                input_bytes=source_bytes,
            )
            if not isinstance(canonical_object_id, bytes):
                raise _QualificationBootstrapError(
                    "qualification bootstrap reviewed source hash is invalid"
                )
            if canonical_object_id.strip() != object_id:
                raise _QualificationBootstrapError(
                    "qualification bootstrap reviewed source bytes changed: "
                    f"{relative_path}"
                )
    except UnicodeDecodeError as exc:
        raise _QualificationBootstrapError(
            f"qualification bootstrap review tree path is not UTF-8: {exc}"
        ) from exc


def _qualification_bootstrap_validate_source(
    repo_root: Path,
    *,
    expected_review_commit: str,
) -> None:
    repo_root = _qualification_bootstrap_require_path(
        repo_root,
        "repository root",
        expected_kind="directory",
    )
    git_root = _qualification_bootstrap_validate_git_metadata(repo_root)
    observed_head = _qualification_bootstrap_git_output(
        repo_root,
        git_root,
        "rev-parse",
        "--verify",
        "HEAD^{commit}",
    )
    if (
        not isinstance(observed_head, str)
        or observed_head.strip() != expected_review_commit
    ):
        raise _QualificationBootstrapError(
            "qualification bootstrap HEAD does not match the review commit"
        )
    _qualification_bootstrap_validate_reviewed_source_bytes(
        repo_root,
        git_root,
        expected_review_commit,
    )
    status = _qualification_bootstrap_git_output(
        repo_root,
        git_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=no",
    )
    if status:
        raise _QualificationBootstrapError(
            "qualification bootstrap source has tracked changes"
        )
    tracked_raw = _qualification_bootstrap_git_output(
        repo_root,
        git_root,
        "ls-files",
        "-v",
        "-z",
        binary=True,
    )
    if not isinstance(tracked_raw, bytes):
        raise _QualificationBootstrapError(
            "qualification bootstrap tracked inventory is invalid"
        )
    tracked_paths = set()
    try:
        for row in tracked_raw.split(b"\0"):
            if not row:
                continue
            if len(row) < 3 or row[1:2] != b" ":
                raise _QualificationBootstrapError(
                    "qualification bootstrap index row is invalid"
                )
            status_tag = chr(row[0])
            if status_tag != "H":
                raise _QualificationBootstrapError(
                    "qualification bootstrap source has a forbidden index flag: "
                    f"{status_tag}"
                )
            tracked_paths.add(row[2:].decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise _QualificationBootstrapError(
            f"qualification bootstrap source path is not UTF-8: {exc}"
        ) from exc
    untracked_executable = []
    for path, metadata in _qualification_bootstrap_walk(
        repo_root,
        skip_root_git=True,
    ):
        relative_path = path.relative_to(repo_root).as_posix()
        if relative_path in tracked_paths or not stat.S_ISREG(metadata.st_mode):
            continue
        if _qualification_bootstrap_path_may_execute(relative_path):
            untracked_executable.append(relative_path)
    if untracked_executable:
        raise _QualificationBootstrapError(
            "qualification bootstrap source has untracked executable paths: "
            + ", ".join(sorted(untracked_executable))
        )


if _QUALIFICATION_CLI_REQUESTED:
    try:
        _qualification_bootstrap_validate_source(
            REPO_ROOT,
            expected_review_commit=_qualification_bootstrap_review_commit(
                tuple(sys.argv[2:])
            ),
        )
    except Exception:
        raise SystemExit(2)


def _contains_project_package(search_root: str) -> bool:
    try:
        root = Path(search_root or os.getcwd()).resolve()
    except OSError:
        return False
    return any(
        (root / name).exists() for name in ("analysis_scripts", "spirecomm")
    )


sys.path[:] = [
    search_root
    for search_root in sys.path
    if not _contains_project_package(search_root)
]
sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.noncombat_outcome_evidence_expansion import (
    OutcomeEvidenceRegistration,
    OutcomeEvidenceRegistrationError,
    RegisteredSlot,
    build_registered_pool,
    collect_registered_session_evidence,
    conservative_marker_run_pairs,
    create_run_lock,
    finalize_registered_integrity_stop,
    finalize_registered_outcome_evidence,
    load_registration,
    manifest_isolation_matches_run_lock,
    registration_handshake_rules,
    require_launchable_registration,
    validate_run_lock,
)
from spirecomm.ai.noncombat_exploration import (
    CONFIG_ENV,
    CONFIG_SCHEMA_VERSION,
    load_exploration_config,
    parse_exploration_config,
)
from spirecomm.communication.study_handshake import (
    HANDSHAKE_ATTEMPT_ENV,
    POLL_INTERVAL_SECONDS,
    HandshakePaths,
    build_attempt_record,
    build_release_record,
    load_attempt_record,
    load_ready_record,
    load_release_record,
    publish_record_once,
    validate_ready_record,
)


LEDGER_SCHEMA_VERSION = "noncombat-outcome-evidence-ledger-v1"
MONITOR_SCHEMA_VERSION = "noncombat-outcome-evidence-blinded-monitor-v2"
LEGACY_QUALIFICATION_REQUEST_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-request-v1"
)
QUALIFICATION_REQUEST_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-request-v2"
)
QUALIFICATION_ISOLATION_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-isolation-v1"
)
QUALIFICATION_ISOLATION_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-isolation-observation-v1"
)
LEGACY_QUALIFICATION_RESULT_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-result-v1"
)
QUALIFICATION_RESULT_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-result-v2"
)
QUALIFICATION_REVIEW_BINDING_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-review-binding-v1"
)
QUALIFICATION_ATTEMPT_HASH_ENV = (
    "STS_OUTCOME_EVIDENCE_QUALIFICATION_ATTEMPT_HASH"
)
QUALIFICATION_LOG_PATH_ENV = "STS_AI_LOG_FILE"
QUALIFICATION_GIT_EXECUTABLE = Path(r"C:\Program Files\Git\cmd\git.exe")
_SHA256_LENGTH = 64
_GIT_COMMIT_LENGTH = 40
_PROCESS_TERMINATION_TIMEOUT_SECONDS = 5
_ZERO_RUN_LOCK_HASH = "0" * _SHA256_LENGTH


class OutcomeEvidenceRunnerError(RuntimeError):
    """Raised when a registered launch or ledger transition is invalid."""


@dataclass(frozen=True)
class RegisteredSlotLaunch:
    slot_number: int
    session_id: str
    config_path: str
    command: tuple[str, ...]
    environment: Mapping[str, str]
    config_record: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "command", tuple(self.command))
        object.__setattr__(
            self,
            "environment",
            MappingProxyType(dict(self.environment)),
        )
        object.__setattr__(
            self,
            "config_record",
            MappingProxyType(json.loads(_canonical_json(self.config_record))),
        )


def build_qualification_request(
    *,
    registration_path: Path | str,
    qualification_id: str,
    qualification_root: Path | str,
    config_path: Path | str,
    marker_path: Path | str,
    request_source_path: Path | str,
    review_allowed_paths: Sequence[str] | None = None,
    created_unix_ns: int | None = None,
) -> dict[str, Any]:
    """Build one pre-lock qualification request without publishing it."""

    resolved_registration_path = _qualification_require_no_follow_path(
        registration_path,
        "registration",
        expected_kind="file",
    )
    registration = _load_qualification_registration(
        resolved_registration_path
    )
    repo_root = _qualification_require_no_follow_path(
        registration.repo_root,
        "repository root",
        expected_kind="directory",
    )
    resolved_root = _qualification_require_no_follow_path(
        qualification_root,
        "root",
        expected_kind="directory",
    )
    resolved_config_path = _qualification_require_no_follow_path(
        config_path,
        "config",
        expected_kind="file",
    )
    resolved_marker_path = _qualification_require_no_follow_path(
        marker_path,
        "marker",
        expected_kind="file",
        allow_missing=True,
    )
    resolved_request_source_path = _qualification_require_no_follow_path(
        request_source_path,
        "request source",
        expected_kind="file",
        allow_missing=True,
    )
    try:
        request_source_relative = resolved_request_source_path.relative_to(
            repo_root
        ).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification request source is outside the source repository"
        ) from exc
    _validate_qualification_id(qualification_id)
    source_commit = _tracked_source_commit(repo_root)
    _require_committed_qualification_registration(
        resolved_registration_path,
        repo_root,
        source_commit,
    )
    bindings = _qualification_request_bindings(
        registration=registration,
        registration_path=resolved_registration_path,
        qualification_id=qualification_id,
        qualification_root=resolved_root,
        config_path=resolved_config_path,
        marker_path=resolved_marker_path,
        source_commit=source_commit,
    )
    registration_relative = resolved_registration_path.relative_to(
        repo_root
    ).as_posix()
    allowed_review_paths = _validate_qualification_review_allowed_paths(
        [request_source_relative]
        if review_allowed_paths is None
        else review_allowed_paths,
        request_source_relative=request_source_relative,
        protected_paths={
            registration_relative,
            *registration.to_record()["integrity_rules"][
                "implementation_paths"
            ],
        },
    )
    if resolved_request_source_path == Path(bindings["request_path"]):
        raise OutcomeEvidenceRunnerError(
            "qualification request source must differ from its active path"
        )
    control_paths = _qualification_control_paths(bindings)
    _require_paths_absent(
        control_paths,
        "qualification control artifact exists before request",
    )
    forbidden_paths = tuple(Path(path) for path in bindings["forbidden_paths"])
    _require_paths_absent(
        forbidden_paths,
        "forbidden qualification output exists before request",
    )
    preexisting_files = _qualification_root_inventory(
        resolved_root,
        excluded_paths={*control_paths, *forbidden_paths},
    )
    record = {
        "child_command": bindings["child_command"],
        "completion_path": bindings["completion_path"],
        "config": bindings["config"],
        "created_unix_ns": _timestamp(created_unix_ns),
        "failure_path": bindings["failure_path"],
        "forbidden_paths": bindings["forbidden_paths"],
        "handshake": bindings["handshake"],
        "implementation_sha256": bindings["implementation_sha256"],
        "isolation": _qualification_build_isolation_baseline(
            registration,
            resolved_marker_path,
        ),
        "marker": bindings["marker"],
        "preexisting_files": preexisting_files,
        "qualification_id": qualification_id,
        "qualification_root": str(resolved_root),
        "registration": bindings["registration"],
        "request_hash": None,
        "request_path": bindings["request_path"],
        "request_source_path": str(resolved_request_source_path),
        "review_allowed_paths": allowed_review_paths,
        "schema_version": QUALIFICATION_REQUEST_SCHEMA_VERSION,
        "source_commit": source_commit,
    }
    record["request_hash"] = _self_hash(record, "request_hash")
    return json.loads(_canonical_json(record))


def load_qualification_request(
    path: Path | str,
    *,
    registration_path: Path | str,
    _source_mode: bool = False,
    _expected_request_hash: str | None = None,
    _expected_review_commit: str | None = None,
    _expected_request_file_sha256: str | None = None,
    _expected_request_size: int | None = None,
) -> dict[str, Any]:
    """Strictly replay a canonical request against current source and files."""

    request_path = _qualification_require_no_follow_path(
        path,
        "request",
        expected_kind="file",
    )
    try:
        raw = request_path.read_bytes()
        record = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except OutcomeEvidenceRunnerError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot load qualification request: {exc}"
        ) from exc
    if not isinstance(record, dict):
        raise OutcomeEvidenceRunnerError("qualification request must be an object")
    if raw != (_canonical_json(record) + "\n").encode("utf-8"):
        raise OutcomeEvidenceRunnerError("qualification request is not canonical")
    if record.get("schema_version") != QUALIFICATION_REQUEST_SCHEMA_VERSION:
        raise OutcomeEvidenceRunnerError("qualification request schema mismatch")
    expected_fields = {
        "child_command",
        "completion_path",
        "config",
        "created_unix_ns",
        "failure_path",
        "forbidden_paths",
        "handshake",
        "implementation_sha256",
        "isolation",
        "marker",
        "preexisting_files",
        "qualification_id",
        "qualification_root",
        "registration",
        "request_hash",
        "request_path",
        "request_source_path",
        "review_allowed_paths",
        "schema_version",
        "source_commit",
    }
    if set(record) != expected_fields:
        raise OutcomeEvidenceRunnerError("qualification request fields mismatch")
    supplied_hash = record["request_hash"]
    if not isinstance(supplied_hash, str) or not _is_lower_hex(
        supplied_hash,
        _SHA256_LENGTH,
    ):
        raise OutcomeEvidenceRunnerError("qualification request hash is invalid")
    if supplied_hash != _self_hash(record, "request_hash"):
        raise OutcomeEvidenceRunnerError("qualification request hash mismatch")
    if (
        _expected_request_hash is not None
        and supplied_hash != _expected_request_hash
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification request differs from the reviewed hash"
        )
    _timestamp(record["created_unix_ns"])
    qualification_id = record["qualification_id"]
    _validate_qualification_id(qualification_id)
    qualification_root = _resolved_absolute_path(
        record["qualification_root"],
        "qualification_root",
    )
    qualification_root = _qualification_require_no_follow_path(
        qualification_root,
        "root",
        expected_kind="directory",
    )
    bound_request_path = _resolved_absolute_path(
        record["request_path"],
        "qualification request path",
    )
    bound_request_source_path = _resolved_absolute_path(
        record["request_source_path"],
        "qualification request source path",
    )
    if bound_request_path.parent != qualification_root:
        raise OutcomeEvidenceRunnerError(
            "qualification request is outside its bound root"
        )
    if bound_request_source_path == bound_request_path:
        raise OutcomeEvidenceRunnerError(
            "qualification request source must differ from its active path"
        )
    if not _source_mode and bound_request_path != request_path:
        raise OutcomeEvidenceRunnerError("qualification request path mismatch")
    if _source_mode and bound_request_source_path != request_path:
        raise OutcomeEvidenceRunnerError(
            "qualification request source path mismatch"
        )

    resolved_registration_path = _qualification_require_no_follow_path(
        registration_path,
        "registration",
        expected_kind="file",
    )
    registration = _load_qualification_registration(
        resolved_registration_path
    )
    source_commit = record["source_commit"]
    if not isinstance(source_commit, str) or not _is_lower_hex(
        source_commit,
        _GIT_COMMIT_LENGTH,
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification source commit is invalid"
        )
    repo_root = _qualification_require_no_follow_path(
        registration.repo_root,
        "repository root",
        expected_kind="directory",
    )
    try:
        request_source_relative = bound_request_source_path.relative_to(
            repo_root
        ).as_posix()
        registration_relative = resolved_registration_path.relative_to(
            repo_root
        ).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification review path is outside the source repository"
        ) from exc
    _validate_qualification_review_allowed_paths(
        record["review_allowed_paths"],
        request_source_relative=request_source_relative,
        protected_paths={
            registration_relative,
            *registration.to_record()["integrity_rules"][
                "implementation_paths"
            ],
        },
    )
    if _source_mode:
        _validate_qualification_review_chain(
            request=record,
            request_source_path=bound_request_source_path,
            expected_request_bytes=raw,
            expected_review_commit=_expected_review_commit,
            expected_request_file_sha256=_expected_request_file_sha256,
            expected_request_size=_expected_request_size,
            registration=registration,
            registration_path=resolved_registration_path,
            implementation_sha256=record["implementation_sha256"],
        )
    config_record = record["config"]
    marker_record = record["marker"]
    if not isinstance(config_record, Mapping) or set(config_record) != {
        "path",
        "sha256",
    }:
        raise OutcomeEvidenceRunnerError("qualification config binding is invalid")
    if not isinstance(marker_record, Mapping) or set(marker_record) != {
        "path",
        "start_count",
    }:
        raise OutcomeEvidenceRunnerError("qualification marker binding is invalid")
    bindings = _qualification_request_bindings(
        registration=registration,
        registration_path=resolved_registration_path,
        qualification_id=qualification_id,
        qualification_root=qualification_root,
        config_path=_resolved_absolute_path(
            config_record["path"],
            "qualification config path",
        ),
        marker_path=_resolved_absolute_path(
            marker_record["path"],
            "qualification marker path",
        ),
        source_commit=source_commit,
    )
    _validate_qualification_isolation_baseline(
        record["isolation"],
        registration=registration,
        marker_path=Path(bindings["marker"]["path"]),
        marker_start_count=bindings["marker"]["start_count"],
    )
    for field in (
        "child_command",
        "completion_path",
        "config",
        "failure_path",
        "forbidden_paths",
        "handshake",
        "implementation_sha256",
        "marker",
        "registration",
        "request_path",
    ):
        if record[field] != bindings[field]:
            raise OutcomeEvidenceRunnerError(
                f"qualification {field.replace('_', ' ')} mismatch"
            )
    control_paths = _qualification_control_paths(bindings)
    _require_paths_absent(
        control_paths if _source_mode else control_paths[1:],
        "qualification control artifact exists before launch",
    )
    forbidden_paths = tuple(Path(path) for path in bindings["forbidden_paths"])
    _require_paths_absent(
        forbidden_paths,
        "forbidden qualification output exists before launch",
    )
    expected_inventory = _qualification_root_inventory(
        qualification_root,
        excluded_paths={*control_paths, *forbidden_paths},
    )
    if record["preexisting_files"] != expected_inventory:
        raise OutcomeEvidenceRunnerError(
            "qualification preexisting file inventory mismatch"
        )
    return json.loads(_canonical_json(record))


def load_qualification_request_source(
    path: Path | str,
    *,
    registration_path: Path | str,
    expected_request_hash: str,
    expected_review_commit: str,
    expected_request_file_sha256: str,
    expected_request_size: int,
) -> dict[str, Any]:
    if not isinstance(expected_request_hash, str) or not _is_lower_hex(
        expected_request_hash,
        _SHA256_LENGTH,
    ):
        raise OutcomeEvidenceRunnerError(
            "reviewed qualification request hash is invalid"
        )
    return load_qualification_request(
        path,
        registration_path=registration_path,
        _source_mode=True,
        _expected_request_hash=expected_request_hash,
        _expected_review_commit=expected_review_commit,
        _expected_request_file_sha256=expected_request_file_sha256,
        _expected_request_size=expected_request_size,
    )


def _validate_qualification_review_allowed_paths(
    value: Any,
    *,
    request_source_relative: str,
    protected_paths: set[str],
) -> list[str]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise OutcomeEvidenceRunnerError(
            "qualification review allowed paths must be a list"
        )
    paths = list(value)
    if (
        not paths
        or any(not isinstance(path, str) or not path for path in paths)
        or paths != sorted(set(paths))
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification review allowed paths are invalid"
        )
    for path in paths:
        candidate = Path(path)
        if (
            candidate.is_absolute()
            or "\\" in path
            or candidate.as_posix() != path
            or any(part in {"", ".", ".."} for part in candidate.parts)
        ):
            raise OutcomeEvidenceRunnerError(
                "qualification review allowed path is not canonical"
            )
        if _qualification_review_path_is_executable(path):
            raise OutcomeEvidenceRunnerError(
                "qualification review allowlist contains an executable path"
            )
    if request_source_relative not in paths:
        raise OutcomeEvidenceRunnerError(
            "qualification request source is absent from the review allowlist"
        )
    overlap = set(paths) & protected_paths
    if overlap:
        raise OutcomeEvidenceRunnerError(
            "qualification review allowlist contains protected paths"
        )
    return paths


def _qualification_review_path_is_executable(relative_path: str) -> bool:
    return _qualification_bootstrap_path_may_execute(relative_path)


def _qualification_request_bindings(
    *,
    registration: OutcomeEvidenceRegistration,
    registration_path: Path,
    qualification_id: str,
    qualification_root: Path,
    config_path: Path,
    marker_path: Path,
    source_commit: str,
) -> dict[str, Any]:
    qualification_root = _qualification_require_no_follow_path(
        qualification_root,
        "root",
        expected_kind="directory",
    )
    config_path = _qualification_require_no_follow_path(
        config_path,
        "config",
        expected_kind="file",
    )
    marker_path = _qualification_require_no_follow_path(
        marker_path,
        "marker",
        expected_kind="file",
        allow_missing=True,
    )
    checkpoint_root = _qualification_require_no_follow_path(
        registration.checkpoint_root,
        "checkpoint root",
        expected_kind="directory",
        allow_missing=True,
    )
    expected_marker_path = (
        checkpoint_root.parent
        / "runs"
        / "ai_games.txt"
    )
    if marker_path != expected_marker_path:
        raise OutcomeEvidenceRunnerError(
            "qualification marker path does not match the registered game root"
        )
    if not config_path.is_relative_to(qualification_root):
        raise OutcomeEvidenceRunnerError(
            "qualification config must be inside the qualification root"
        )
    config = _load_qualification_exploration_config(config_path)
    registered_behavior = registration.to_record()["behavior"]
    if (
        list(config.enabled_categories)
        != registered_behavior["enabled_categories"]
        or dict(config.category_rates_bps)
        != registered_behavior["category_rates_bps"]
        or config.per_run_alternative_budget
        != registered_behavior["per_run_alternative_budget"]
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification configuration behavior differs from registration"
        )
    session_id = f"{qualification_id}-s01"
    if (
        config.session_id != session_id
        or config.source_commit != source_commit
        or config.study_id != qualification_id
        or config.study_slot_number != 1
        or config.study_registration_hash != registration.registration_hash
        or config.study_run_lock_hash != _ZERO_RUN_LOCK_HASH
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification exploration config binding mismatch"
        )
    rules = registration_handshake_rules(registration)
    if rules is None:
        raise OutcomeEvidenceRunnerError(
            "launchable registration has no handshake rules"
        )
    attempt_path = Path(
        os.path.abspath(
            qualification_root / "qualification-communication-attempt.json"
        )
    )
    ready_path = Path(
        os.path.abspath(
            qualification_root / "qualification-communication-ready.json"
        )
    )
    release_path = Path(
        os.path.abspath(
            qualification_root / "qualification-communication-release.json"
        )
    )
    completion_path = Path(
        os.path.abspath(qualification_root / "qualification-completion.json")
    )
    failure_path = Path(
        os.path.abspath(qualification_root / "qualification-failure.json")
    )
    request_path = Path(
        os.path.abspath(qualification_root / "qualification-request.json")
    )
    registered_root = _qualification_require_no_follow_path(
        registration.artifact_root,
        "registered artifact root",
        expected_kind="directory",
        allow_missing=True,
    )
    forbidden_paths = sorted(
        {
            str(registered_root),
            str(Path(os.path.abspath(registered_root / "run-lock.json"))),
            str(Path(os.path.abspath(registered_root / "study-ledger.jsonl"))),
            str(config.manifest_path),
            str(config.trace_path),
        }
    )
    return {
        "child_command": _qualification_child_command(registration),
        "completion_path": str(completion_path),
        "config": {
            "path": str(config_path),
            "sha256": _path_sha256(config_path, "qualification config"),
        },
        "failure_path": str(failure_path),
        "forbidden_paths": forbidden_paths,
        "handshake": {
            "attempt_path": str(attempt_path),
            "protocol_version": rules["protocol_version"],
            "readiness_timeout_seconds": rules["readiness_timeout_seconds"],
            "ready_path": str(ready_path),
            "release_path": str(release_path),
            "release_timeout_seconds": rules["release_timeout_seconds"],
            "run_lock_hash": _ZERO_RUN_LOCK_HASH,
            "session_id": session_id,
            "slot_number": 1,
        },
        "implementation_sha256": _qualification_implementation_sha256(
            registration
        ),
        "marker": {
            "path": str(marker_path),
            "start_count": _ai_marker_count(marker_path),
        },
        "registration": {
            "canonical_hash": registration.registration_hash,
            "file_sha256": _path_sha256(
                registration_path,
                "qualification registration",
            ),
            "path": str(registration_path),
        },
        "request_path": str(request_path),
    }


def _qualification_build_isolation_baseline(
    registration: OutcomeEvidenceRegistration,
    marker_path: Path,
) -> dict[str, Any]:
    checkpoint_root = _qualification_require_no_follow_path(
        registration.checkpoint_root,
        "qualification checkpoint isolation root",
        expected_kind="directory",
    )
    game_root = checkpoint_root.parent
    run_root = _qualification_require_no_follow_path(
        game_root / "runs",
        "qualification run isolation root",
        expected_kind="directory",
    )
    resolved_marker_path = _qualification_require_no_follow_path(
        marker_path,
        "qualification isolation marker",
        expected_kind="file",
        allow_missing=True,
    )
    if resolved_marker_path != run_root / "ai_games.txt":
        raise OutcomeEvidenceRunnerError(
            "qualification isolation marker does not match the run root"
        )
    communication_path = _qualification_require_no_follow_path(
        registration.communication_config_path,
        "qualification CommunicationMod config",
        expected_kind="file",
    )
    communication_bytes = _qualification_read_file_bytes(
        communication_path,
        "qualification CommunicationMod config",
    )
    communication = {
        "original_bytes_b64": base64.b64encode(communication_bytes).decode(
            "ascii"
        ),
        "path": str(communication_path),
        "properties": _qualification_parse_java_properties(
            communication_bytes
        ),
        "sha256": hashlib.sha256(communication_bytes).hexdigest(),
        "size": len(communication_bytes),
    }
    marker, marker_bytes = _qualification_file_observation_bytes(
        resolved_marker_path,
        label="qualification isolation marker",
        allow_missing=True,
    )
    marker["line_count"] = _qualification_marker_count_from_bytes(
        marker_bytes
    )
    checkpoint_patterns = tuple(
        registration.to_record()["integrity_rules"]["checkpoint_inventory"][
            "patterns"
        ]
    )
    log_paths = (
        game_root / "ai_debug.log",
        game_root / "communication_mod_errors.log",
    )
    record = {
        "baseline_hash": None,
        "checkpoints": _qualification_inventory_observation(
            checkpoint_root,
            patterns=checkpoint_patterns,
        ),
        "communication_mod": communication,
        "global_logs": {
            str(Path(os.path.abspath(path))): _qualification_file_observation(
                path,
                label="qualification global log",
                allow_missing=True,
            )
            for path in log_paths
        },
        "marker": marker,
        "runs": _qualification_inventory_observation(run_root),
        "schema_version": QUALIFICATION_ISOLATION_SCHEMA_VERSION,
    }
    record["baseline_hash"] = _self_hash(record, "baseline_hash")
    return _validate_qualification_isolation_baseline(
        record,
        registration=registration,
        marker_path=resolved_marker_path,
        marker_start_count=marker["line_count"],
    )


def _qualification_file_observation(
    path: Path,
    *,
    label: str,
    allow_missing: bool,
) -> dict[str, Any]:
    observation, _raw = _qualification_file_observation_bytes(
        path,
        label=label,
        allow_missing=allow_missing,
    )
    return observation


def _qualification_file_observation_bytes(
    path: Path,
    *,
    label: str,
    allow_missing: bool,
) -> tuple[dict[str, Any], bytes | None]:
    guarded_path = _qualification_require_no_follow_path(
        path,
        label,
        expected_kind="file",
        allow_missing=allow_missing,
    )
    if not _qualification_path_entry_exists(guarded_path):
        return (
            {
                "exists": False,
                "path": str(guarded_path),
                "sha256": None,
                "size": None,
            },
            None,
        )
    raw = _qualification_read_file_bytes(guarded_path, label)
    return (
        {
            "exists": True,
            "path": str(guarded_path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        },
        raw,
    )


def _qualification_marker_count_from_bytes(raw: bytes | None) -> int:
    if raw is None:
        return 0
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot decode qualification AI marker file: {exc}"
        ) from exc
    markers = [line.strip() for line in lines if line.strip()]
    if any(not marker.isdigit() for marker in markers):
        raise OutcomeEvidenceRunnerError(
            "qualification AI marker file contains an invalid marker"
        )
    return len(markers)


def _qualification_inventory_observation(
    root: Path,
    *,
    patterns: Sequence[str] | None = None,
) -> dict[str, Any]:
    guarded_root = _qualification_require_no_follow_path(
        root,
        "qualification isolation inventory root",
        expected_kind="directory",
    )
    normalized_patterns = None
    if patterns is not None:
        normalized_patterns = list(patterns)
        if (
            not normalized_patterns
            or normalized_patterns != sorted(set(normalized_patterns))
            or any(
                not isinstance(pattern, str)
                or not pattern
                or "/" in pattern
                or "\\" in pattern
                or pattern in {".", ".."}
                for pattern in normalized_patterns
            )
        ):
            raise OutcomeEvidenceRunnerError(
                "qualification isolation inventory patterns are invalid"
            )
    rows = []
    for path, metadata, is_link_or_reparse in _qualification_no_follow_entries(
        guarded_root
    ):
        if is_link_or_reparse:
            raise OutcomeEvidenceRunnerError(
                "qualification isolation inventory contains a link or "
                "reparse point"
            )
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise OutcomeEvidenceRunnerError(
                "qualification isolation inventory contains a non-regular "
                "entry"
            )
        if normalized_patterns is not None and not any(
            path.match(pattern) for pattern in normalized_patterns
        ):
            continue
        raw = _qualification_read_file_bytes(
            path,
            "qualification isolation inventory file",
        )
        rows.append(
            {
                "kind": "file",
                "path": path.relative_to(guarded_root).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            }
        )
    rows.sort(key=lambda row: row["path"])
    return {
        "entry_count": len(rows),
        "inventory_sha256": hashlib.sha256(
            _canonical_json(rows).encode("utf-8")
        ).hexdigest(),
        "patterns": normalized_patterns,
        "root": str(guarded_root),
        "total_bytes": sum(row["size"] for row in rows),
    }


def _qualification_read_file_bytes(path: Path, label: str) -> bytes:
    guarded_path = _qualification_require_no_follow_path(
        path,
        label,
        expected_kind="file",
    )
    try:
        before = guarded_path.lstat()
        with open(guarded_path, "rb") as stream:
            handle_before = os.fstat(stream.fileno())
            opened_path = guarded_path.lstat()
            raw = stream.read()
            handle_after = os.fstat(stream.fileno())
        guarded_after = _qualification_require_no_follow_path(
            guarded_path,
            label,
            expected_kind="file",
        )
        after = guarded_after.lstat()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(f"cannot read {label}: {exc}") from exc

    metadata_rows = (
        before,
        handle_before,
        opened_path,
        handle_after,
        after,
    )
    signatures = {
        (
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        for metadata in metadata_rows
    }
    if (
        any(
            _qualification_metadata_is_link_or_reparse(metadata)
            or not stat.S_ISREG(metadata.st_mode)
            for metadata in metadata_rows
        )
        or any(
            not os.path.samestat(before, metadata)
            for metadata in metadata_rows[1:]
        )
        or len(signatures) != 1
        or len(raw) != handle_after.st_size
    ):
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} changed while being read"
        )
    return raw


def _qualification_parse_java_properties(raw: bytes) -> dict[str, str]:
    content = raw.decode("iso-8859-1")
    natural_lines = (
        content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    )
    properties: dict[str, str] = {}
    for logical_line in _qualification_java_properties_logical_lines(
        natural_lines
    ):
        parsed = _qualification_parse_java_property(logical_line)
        if parsed is None:
            continue
        key, value = parsed
        if key in properties:
            raise OutcomeEvidenceRunnerError(
                "qualification CommunicationMod config contains a duplicate "
                "property"
            )
        properties[key] = value
    return properties


def _qualification_java_properties_logical_lines(
    lines: Sequence[str],
):
    pending = ""
    continuing = False
    for natural_line in lines:
        if not continuing and natural_line.lstrip(" \t\f").startswith(
            ("#", "!")
        ):
            yield natural_line
            continue
        piece = natural_line.lstrip(" \t\f") if continuing else natural_line
        pending += piece
        trailing_backslashes = len(pending) - len(pending.rstrip("\\"))
        if trailing_backslashes % 2 == 1:
            pending = pending[:-1]
            continuing = True
            continue
        yield pending
        pending = ""
        continuing = False
    if pending or continuing:
        yield pending


def _qualification_parse_java_property(
    line: str,
) -> tuple[str, str] | None:
    content = line.lstrip(" \t\f")
    if not content or content.startswith(("#", "!")):
        return None
    key_end = len(content)
    value_start = len(content)
    escaped = False
    for index, character in enumerate(content):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character in "=: \t\f":
            key_end = index
            value_start = index
            break
    while value_start < len(content) and content[value_start] in " \t\f":
        value_start += 1
    if value_start < len(content) and content[value_start] in "=:":
        value_start += 1
    while value_start < len(content) and content[value_start] in " \t\f":
        value_start += 1
    return (
        _qualification_decode_java_property_escapes(content[:key_end]),
        _qualification_decode_java_property_escapes(content[value_start:]),
    )


def _qualification_decode_java_property_escapes(value: str) -> str:
    decoded = []
    index = 0
    escapes = {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}
    while index < len(value):
        character = value[index]
        if character != "\\":
            decoded.append(character)
            index += 1
            continue
        index += 1
        if index >= len(value):
            raise OutcomeEvidenceRunnerError(
                "invalid trailing escape in CommunicationMod config"
            )
        escaped = value[index]
        if escaped == "u":
            digits = value[index + 1 : index + 5]
            if len(digits) != 4 or any(
                digit not in "0123456789abcdefABCDEF" for digit in digits
            ):
                raise OutcomeEvidenceRunnerError(
                    "invalid Unicode escape in CommunicationMod config"
                )
            decoded.append(chr(int(digits, 16)))
            index += 5
            continue
        decoded.append(escapes.get(escaped, escaped))
        index += 1
    return "".join(decoded)


def _validate_qualification_isolation_baseline(
    value: Any,
    *,
    registration: OutcomeEvidenceRegistration,
    marker_path: Path,
    marker_start_count: int,
) -> dict[str, Any]:
    expected_fields = {
        "baseline_hash",
        "checkpoints",
        "communication_mod",
        "global_logs",
        "marker",
        "runs",
        "schema_version",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise OutcomeEvidenceRunnerError(
            "qualification isolation baseline fields mismatch"
        )
    record = dict(value)
    if record["schema_version"] != QUALIFICATION_ISOLATION_SCHEMA_VERSION:
        raise OutcomeEvidenceRunnerError(
            "qualification isolation baseline schema mismatch"
        )
    baseline_hash = record["baseline_hash"]
    if (
        not isinstance(baseline_hash, str)
        or not _is_lower_hex(baseline_hash, _SHA256_LENGTH)
        or baseline_hash != _self_hash(record, "baseline_hash")
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification isolation baseline hash mismatch"
        )
    checkpoint_root = Path(registration.checkpoint_root)
    game_root = checkpoint_root.parent
    _validate_qualification_inventory_observation(
        record["checkpoints"],
        expected_root=checkpoint_root,
        expected_patterns=registration.to_record()["integrity_rules"][
            "checkpoint_inventory"
        ]["patterns"],
        label="checkpoint",
    )
    _validate_qualification_inventory_observation(
        record["runs"],
        expected_root=game_root / "runs",
        expected_patterns=None,
        label="run",
    )
    communication = record["communication_mod"]
    if not isinstance(communication, Mapping) or set(communication) != {
        "original_bytes_b64",
        "path",
        "properties",
        "sha256",
        "size",
    }:
        raise OutcomeEvidenceRunnerError(
            "qualification CommunicationMod isolation binding is invalid"
        )
    communication_path = _resolved_absolute_path(
        communication["path"],
        "qualification CommunicationMod isolation path",
    )
    if communication_path != Path(registration.communication_config_path):
        raise OutcomeEvidenceRunnerError(
            "qualification CommunicationMod isolation path mismatch"
        )
    try:
        original_bytes = base64.b64decode(
            communication["original_bytes_b64"],
            validate=True,
        )
    except (TypeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification CommunicationMod original bytes are invalid"
        ) from exc
    if (
        type(communication["size"]) is not int
        or communication["size"] < 0
        or len(original_bytes) != communication["size"]
        or not isinstance(communication["sha256"], str)
        or hashlib.sha256(original_bytes).hexdigest()
        != communication["sha256"]
        or not isinstance(communication["properties"], Mapping)
        or dict(communication["properties"])
        != _qualification_parse_java_properties(original_bytes)
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification CommunicationMod original-byte binding mismatch"
        )
    marker = record["marker"]
    _validate_qualification_file_observation(
        marker,
        expected_path=marker_path,
        label="marker",
        extra_fields={"line_count"},
    )
    if (
        type(marker["line_count"]) is not int
        or marker["line_count"] < 0
        or marker["line_count"] != marker_start_count
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification isolation marker count mismatch"
        )
    global_logs = record["global_logs"]
    expected_logs = {
        str(Path(os.path.abspath(game_root / "ai_debug.log"))),
        str(
            Path(
                os.path.abspath(game_root / "communication_mod_errors.log")
            )
        ),
    }
    if not isinstance(global_logs, Mapping) or set(global_logs) != expected_logs:
        raise OutcomeEvidenceRunnerError(
            "qualification global-log isolation paths mismatch"
        )
    for path, observation in global_logs.items():
        _validate_qualification_file_observation(
            observation,
            expected_path=Path(path),
            label="global log",
        )
    return json.loads(_canonical_json(record))


def _validate_qualification_file_observation(
    value: Any,
    *,
    expected_path: Path,
    label: str,
    extra_fields: set[str] | None = None,
) -> None:
    extras = set() if extra_fields is None else set(extra_fields)
    if not isinstance(value, Mapping) or set(value) != {
        "exists",
        "path",
        "sha256",
        "size",
        *extras,
    }:
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} isolation observation is invalid"
        )
    observed_path = _resolved_absolute_path(
        value["path"],
        f"qualification {label} isolation path",
    )
    if observed_path != Path(expected_path):
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} isolation path mismatch"
        )
    exists = value["exists"]
    if type(exists) is not bool:
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} isolation existence is invalid"
        )
    if exists:
        if (
            type(value["size"]) is not int
            or value["size"] < 0
            or not isinstance(value["sha256"], str)
            or not _is_lower_hex(value["sha256"], _SHA256_LENGTH)
        ):
            raise OutcomeEvidenceRunnerError(
                f"qualification {label} isolation fingerprint is invalid"
            )
    elif value["size"] is not None or value["sha256"] is not None:
        raise OutcomeEvidenceRunnerError(
            f"qualification absent {label} isolation fingerprint is invalid"
        )


def _validate_qualification_inventory_observation(
    value: Any,
    *,
    expected_root: Path,
    expected_patterns: Sequence[str] | None,
    label: str,
) -> None:
    if not isinstance(value, Mapping) or set(value) != {
        "entry_count",
        "inventory_sha256",
        "patterns",
        "root",
        "total_bytes",
    }:
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} isolation inventory is invalid"
        )
    root = _resolved_absolute_path(
        value["root"],
        f"qualification {label} isolation root",
    )
    normalized_expected_patterns = (
        None if expected_patterns is None else list(expected_patterns)
    )
    if (
        root != Path(expected_root)
        or value["patterns"] != normalized_expected_patterns
        or type(value["entry_count"]) is not int
        or value["entry_count"] < 0
        or type(value["total_bytes"]) is not int
        or value["total_bytes"] < 0
        or not isinstance(value["inventory_sha256"], str)
        or not _is_lower_hex(value["inventory_sha256"], _SHA256_LENGTH)
    ):
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} isolation inventory binding mismatch"
        )


def _qualification_expected_isolation_observation(
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    communication = baseline["communication_mod"]
    record = {
        "checkpoints": dict(baseline["checkpoints"]),
        "communication_mod": {
            "exists": True,
            "path": communication["path"],
            "properties": dict(communication["properties"]),
            "sha256": communication["sha256"],
            "size": communication["size"],
        },
        "global_logs": {
            path: dict(observation)
            for path, observation in baseline["global_logs"].items()
        },
        "marker": dict(baseline["marker"]),
        "observation_hash": None,
        "runs": dict(baseline["runs"]),
        "schema_version": QUALIFICATION_ISOLATION_OBSERVATION_SCHEMA_VERSION,
    }
    record["observation_hash"] = _self_hash(record, "observation_hash")
    return record


def _qualification_observe_isolation(
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    communication_baseline = baseline["communication_mod"]
    communication_path = Path(communication_baseline["path"])
    communication, communication_bytes = _qualification_file_observation_bytes(
        communication_path,
        label="qualification CommunicationMod observation",
        allow_missing=True,
    )
    if communication["exists"]:
        communication["properties"] = _qualification_parse_java_properties(
            communication_bytes
        )
    else:
        communication["properties"] = None

    marker_path = Path(baseline["marker"]["path"])
    marker, marker_bytes = _qualification_file_observation_bytes(
        marker_path,
        label="qualification marker observation",
        allow_missing=True,
    )
    marker["line_count"] = _qualification_marker_count_from_bytes(marker_bytes)

    checkpoint_baseline = baseline["checkpoints"]
    run_baseline = baseline["runs"]
    record = {
        "checkpoints": _qualification_inventory_observation(
            Path(checkpoint_baseline["root"]),
            patterns=checkpoint_baseline["patterns"],
        ),
        "communication_mod": communication,
        "global_logs": {
            path: _qualification_file_observation(
                Path(path),
                label="qualification global-log observation",
                allow_missing=True,
            )
            for path in baseline["global_logs"]
        },
        "marker": marker,
        "observation_hash": None,
        "runs": _qualification_inventory_observation(
            Path(run_baseline["root"]),
            patterns=run_baseline["patterns"],
        ),
        "schema_version": QUALIFICATION_ISOLATION_OBSERVATION_SCHEMA_VERSION,
    }
    record["observation_hash"] = _self_hash(record, "observation_hash")
    return _validate_qualification_isolation_observation(record, baseline)


def _validate_qualification_isolation_observation(
    value: Any,
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    expected_fields = {
        "checkpoints",
        "communication_mod",
        "global_logs",
        "marker",
        "observation_hash",
        "runs",
        "schema_version",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise OutcomeEvidenceRunnerError(
            "qualification isolation observation fields mismatch"
        )
    record = dict(value)
    if (
        record["schema_version"]
        != QUALIFICATION_ISOLATION_OBSERVATION_SCHEMA_VERSION
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification isolation observation schema mismatch"
        )
    observation_hash = record["observation_hash"]
    if (
        not isinstance(observation_hash, str)
        or not _is_lower_hex(observation_hash, _SHA256_LENGTH)
        or observation_hash != _self_hash(record, "observation_hash")
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification isolation observation hash mismatch"
        )

    communication = record["communication_mod"]
    _validate_qualification_file_observation(
        communication,
        expected_path=Path(baseline["communication_mod"]["path"]),
        label="CommunicationMod",
        extra_fields={"properties"},
    )
    if communication["exists"]:
        if not isinstance(communication["properties"], Mapping):
            raise OutcomeEvidenceRunnerError(
                "qualification CommunicationMod properties are invalid"
            )
    elif communication["properties"] is not None:
        raise OutcomeEvidenceRunnerError(
            "qualification absent CommunicationMod properties are invalid"
        )

    marker = record["marker"]
    _validate_qualification_file_observation(
        marker,
        expected_path=Path(baseline["marker"]["path"]),
        label="marker",
        extra_fields={"line_count"},
    )
    if type(marker["line_count"]) is not int or marker["line_count"] < 0:
        raise OutcomeEvidenceRunnerError(
            "qualification marker observation count is invalid"
        )

    for name in ("checkpoints", "runs"):
        inventory_baseline = baseline[name]
        _validate_qualification_inventory_observation(
            record[name],
            expected_root=Path(inventory_baseline["root"]),
            expected_patterns=inventory_baseline["patterns"],
            label=name,
        )
    global_logs = record["global_logs"]
    if (
        not isinstance(global_logs, Mapping)
        or set(global_logs) != set(baseline["global_logs"])
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification global-log observation paths mismatch"
        )
    for path, observation in global_logs.items():
        _validate_qualification_file_observation(
            observation,
            expected_path=Path(path),
            label="global log",
        )
    return json.loads(_canonical_json(record))


def _qualification_isolation_mismatches(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> list[str]:
    mismatches = []
    for name in ("communication_mod", "marker", "runs", "checkpoints"):
        if observed[name] != expected[name]:
            mismatches.append(name)
    for path, expected_log in expected["global_logs"].items():
        if observed["global_logs"].get(path) != expected_log:
            mismatches.append(f"global_log:{path}")
    return sorted(mismatches)


def _qualification_validate_prelaunch_isolation(
    request: Mapping[str, Any],
    qualification_launch_command: Sequence[str] | None,
) -> dict[str, Any]:
    baseline = request["isolation"]
    expected = _qualification_expected_isolation_observation(baseline)
    observed = _qualification_observe_isolation(baseline)
    mismatches = _qualification_isolation_mismatches(expected, observed)
    if qualification_launch_command is not None:
        mismatches = [
            mismatch
            for mismatch in mismatches
            if mismatch != "communication_mod"
        ]
        baseline_properties = dict(
            baseline["communication_mod"]["properties"]
        )
        observed_communication = observed["communication_mod"]
        observed_properties = observed_communication["properties"]
        command_matches = False
        non_command_matches = False
        if observed_communication["exists"] and isinstance(
            observed_properties,
            Mapping,
        ):
            current_properties = dict(observed_properties)
            current_command = current_properties.pop("command", None)
            baseline_command = baseline_properties.pop("command", None)
            command_matches = (
                isinstance(current_command, str)
                and baseline_command is not None
                and current_command.strip().split()
                == list(qualification_launch_command)
            )
            non_command_matches = current_properties == baseline_properties
        if not command_matches or not non_command_matches:
            mismatches.append("communication_mod")
    if mismatches:
        raise OutcomeEvidenceRunnerError(
            "qualification prelaunch isolation mismatch: "
            + ", ".join(sorted(set(mismatches)))
        )
    return observed


def _qualification_restore_communication_config(
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    communication = baseline["communication_mod"]
    try:
        original_bytes = base64.b64decode(
            communication["original_bytes_b64"],
            validate=True,
        )
    except (TypeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification CommunicationMod restoration bytes are invalid"
        ) from exc
    target = _qualification_require_no_follow_path(
        communication["path"],
        "CommunicationMod restoration target",
        expected_kind="file",
        allow_missing=True,
    )
    _qualification_require_no_follow_path(
        target.parent,
        "CommunicationMod restoration parent",
        expected_kind="directory",
    )
    restoration_parent = target.parent
    try:
        parent_before = restoration_parent.lstat()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification CommunicationMod restoration parent cannot be "
            f"inspected: {exc}"
        ) from exc
    descriptor = -1
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.qualification-",
            dir=str(restoration_parent),
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(original_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        _qualification_require_no_follow_path(
            temporary_path,
            "CommunicationMod restoration temporary file",
            expected_kind="file",
        )
        temporary_before = temporary_path.lstat()
        _qualification_require_no_follow_path(
            target,
            "CommunicationMod restoration target",
            expected_kind="file",
            allow_missing=True,
        )
        _qualification_require_no_follow_path(
            restoration_parent,
            "CommunicationMod restoration parent",
            expected_kind="directory",
        )
        parent_before_replace = restoration_parent.lstat()
        temporary_before_replace = temporary_path.lstat()
        if (
            not os.path.samestat(parent_before, parent_before_replace)
            or _qualification_metadata_is_link_or_reparse(
                parent_before_replace
            )
            or not stat.S_ISDIR(parent_before_replace.st_mode)
        ):
            raise OutcomeEvidenceRunnerError(
                "qualification CommunicationMod restoration parent changed "
                "during restoration"
            )
        if (
            not os.path.samestat(
                temporary_before,
                temporary_before_replace,
            )
            or _qualification_metadata_is_link_or_reparse(
                temporary_before_replace
            )
            or not stat.S_ISREG(temporary_before_replace.st_mode)
        ):
            raise OutcomeEvidenceRunnerError(
                "qualification CommunicationMod restoration temporary file "
                "changed during restoration"
            )
        os.replace(temporary_path, target)
        temporary_path = None
        _qualification_require_no_follow_path(
            restoration_parent,
            "CommunicationMod restoration parent",
            expected_kind="directory",
        )
        restored_path = _qualification_require_no_follow_path(
            target,
            "restored CommunicationMod config",
            expected_kind="file",
        )
        parent_after = restoration_parent.lstat()
        restored_metadata = restored_path.lstat()
        if not os.path.samestat(parent_before, parent_after):
            raise OutcomeEvidenceRunnerError(
                "qualification CommunicationMod restoration parent changed "
                "during restoration"
            )
        if not os.path.samestat(temporary_before, restored_metadata):
            raise OutcomeEvidenceRunnerError(
                "qualification CommunicationMod restoration target identity "
                "mismatch"
            )
        restored_bytes = _qualification_read_file_bytes(
            restored_path,
            "restored CommunicationMod config",
        )
        if restored_bytes != original_bytes:
            raise OutcomeEvidenceRunnerError(
                "qualification CommunicationMod restoration byte mismatch"
            )
        observation = _qualification_file_observation(
            restored_path,
            label="restored CommunicationMod config",
            allow_missing=False,
        )
        observation["properties"] = _qualification_parse_java_properties(
            restored_bytes
        )
        return observation
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            f"qualification CommunicationMod restoration failed: {exc}"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _qualification_child_alive(process: Any) -> bool | None:
    if process is None:
        return False
    try:
        return process.poll() is None
    except BaseException:
        return None


def _qualification_finalize_isolation(
    request: Mapping[str, Any],
    process: Any,
) -> dict[str, Any]:
    baseline = request["isolation"]
    restoration_error = None
    observation_error = None
    communication_restored = False
    observed = None
    try:
        _qualification_restore_communication_config(baseline)
        communication_restored = True
    except BaseException as exc:
        restoration_error = f"{type(exc).__name__}: {exc}"
    try:
        observed = _qualification_observe_isolation(baseline)
    except BaseException as exc:
        observation_error = f"{type(exc).__name__}: {exc}"

    child_alive = _qualification_child_alive(process)
    mismatches = []
    if observed is None:
        mismatches.append("observation_error")
    else:
        mismatches.extend(
            _qualification_isolation_mismatches(
                _qualification_expected_isolation_observation(baseline),
                observed,
            )
        )
    if not communication_restored:
        mismatches.append("communication_restore")
    if child_alive is not False:
        mismatches.append("child_process")
    mismatches = sorted(set(mismatches))
    return {
        "baseline_hash": baseline["baseline_hash"],
        "child_alive": child_alive,
        "communication_restored": communication_restored,
        "matched": (
            not mismatches
            and restoration_error is None
            and observation_error is None
        ),
        "mismatches": mismatches,
        "observation_error": observation_error,
        "post_observation": observed,
        "post_observation_hash": (
            None if observed is None else observed["observation_hash"]
        ),
        "restoration_error": restoration_error,
    }


def _load_qualification_exploration_config(path: Path):
    try:
        payload = json.loads(
            path.read_bytes().decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except OutcomeEvidenceRunnerError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(
            f"qualification config is invalid: {exc}"
        ) from exc
    expected_fields = {
        "category_rates_bps",
        "enabled_categories",
        "manifest_path",
        "per_run_alternative_budget",
        "schema_version",
        "seed",
        "session_id",
        "source_commit",
        "study_id",
        "study_registration_hash",
        "study_run_lock_hash",
        "study_slot_number",
        "trace_path",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected_fields:
        raise OutcomeEvidenceRunnerError(
            "qualification configuration fields mismatch"
        )
    for field in ("manifest_path", "trace_path"):
        _qualification_require_no_follow_path(
            payload[field],
            f"configuration {field}",
            expected_kind="file",
            allow_missing=True,
        )
    try:
        return parse_exploration_config(payload, config_path=path)
    except ExplorationConfigurationError as exc:
        raise OutcomeEvidenceRunnerError(
            f"qualification config is invalid: {exc}"
        ) from exc


def _qualification_control_paths(bindings: Mapping[str, Any]) -> tuple[Path, ...]:
    handshake = bindings["handshake"]
    return (
        Path(bindings["request_path"]),
        Path(handshake["attempt_path"]),
        Path(handshake["ready_path"]),
        Path(handshake["release_path"]),
        Path(bindings["completion_path"]),
        Path(bindings["failure_path"]),
    )


def _qualification_root_inventory(
    root: Path,
    *,
    excluded_paths: set[Path],
    deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, str]:
    excluded = {
        Path(os.path.abspath(path)) for path in excluded_paths
    }
    inventory = {}
    for path, metadata, is_link_or_reparse in _qualification_no_follow_entries(
        root,
        deadline=deadline,
        monotonic=monotonic,
    ):
        lexical_path = Path(os.path.abspath(path))
        if is_link_or_reparse:
            raise OutcomeEvidenceRunnerError(
                "qualification root contains a symbolic link or reparse "
                f"point: {path}"
            )
        if lexical_path in excluded or not stat.S_ISREG(metadata.st_mode):
            continue
        inventory[str(lexical_path)] = _path_sha256(
            path,
            "qualification preexisting file",
            deadline=deadline,
            monotonic=monotonic,
        )
    return inventory


def _qualification_metadata_is_link_or_reparse(
    metadata: os.stat_result,
) -> bool:
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        file_attributes & reparse_flag
    )


def _qualification_require_no_follow_path(
    path: Path | str,
    label: str,
    *,
    expected_kind: str | None,
    allow_missing: bool = False,
) -> Path:
    supplied_path = Path(os.fspath(path))
    supplied_components = (
        supplied_path.parts[1:] if supplied_path.anchor else supplied_path.parts
    )
    if any(":" in part for part in supplied_components):
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} contains an alternate data stream"
        )
    if any(part.endswith((".", " ")) for part in supplied_components):
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} contains a Win32 alias component"
        )
    lexical_path = Path(os.path.abspath(supplied_path))
    if lexical_path.drive.startswith("\\\\"):
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} must use a local drive; UNC and device "
            "paths are forbidden"
        )
    if expected_kind not in {None, "directory", "file"}:
        raise OutcomeEvidenceRunnerError(
            "qualification path expected kind is invalid"
        )
    current = Path(lexical_path.anchor)
    for part in lexical_path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError as exc:
            if allow_missing:
                return lexical_path
            raise OutcomeEvidenceRunnerError(
                f"qualification {label} is missing: {current}"
            ) from exc
        except OSError as exc:
            raise OutcomeEvidenceRunnerError(
                f"cannot inspect qualification {label}: {current}: {exc}"
            ) from exc
        if _qualification_metadata_is_link_or_reparse(metadata):
            raise OutcomeEvidenceRunnerError(
                f"qualification {label} contains a symbolic link or reparse "
                f"point: {current}"
            )
    try:
        metadata = lexical_path.lstat()
    except FileNotFoundError as exc:
        if allow_missing:
            return lexical_path
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} is missing: {lexical_path}"
        ) from exc
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot inspect qualification {label}: {lexical_path}: {exc}"
        ) from exc
    if expected_kind is None:
        return lexical_path
    expected_mode = (
        stat.S_ISDIR(metadata.st_mode)
        if expected_kind == "directory"
        else stat.S_ISREG(metadata.st_mode)
    )
    if not expected_mode:
        raise OutcomeEvidenceRunnerError(
            f"qualification {label} is not a regular {expected_kind}: "
            f"{lexical_path}"
        )
    return lexical_path


def _qualification_git_executable() -> str:
    return str(
        _qualification_require_no_follow_path(
            QUALIFICATION_GIT_EXECUTABLE,
            "Git executable",
            expected_kind="file",
        )
    )


def _qualification_git_environment(
    *,
    repo_root: Path,
    git_root: Path,
) -> dict[str, str]:
    environment = {
        key: value
        for key in ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP")
        if (value := os.environ.get(key))
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_DIR": str(git_root),
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_WORK_TREE": str(repo_root),
            "LC_ALL": "C",
        }
    )
    return environment


def _qualification_git_command(*arguments: str) -> list[str]:
    return [
        _qualification_git_executable(),
        "--no-pager",
        "--no-replace-objects",
        "--no-lazy-fetch",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=NUL",
        "-c",
        "diff.external=",
        "-c",
        "color.ui=false",
        *arguments,
    ]


def _qualification_registration_absolute_paths(value: Any):
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _qualification_registration_absolute_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _qualification_registration_absolute_paths(child)
    elif isinstance(value, str) and Path(value).is_absolute():
        yield value


def _load_qualification_registration(
    path: Path | str,
) -> OutcomeEvidenceRegistration:
    registration_path = _qualification_require_no_follow_path(
        path,
        "registration",
        expected_kind="file",
    )
    try:
        payload = json.loads(
            registration_path.read_bytes().decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except OutcomeEvidenceRunnerError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(
            f"qualification registration is invalid: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise OutcomeEvidenceRunnerError(
            "qualification registration must be an object"
        )
    for raw_path in _qualification_registration_absolute_paths(payload):
        _qualification_require_no_follow_path(
            raw_path,
            "registered path",
            expected_kind=None,
            allow_missing=True,
        )
    raw_repo_root = payload.get("repo_root")
    if not isinstance(raw_repo_root, str) or not Path(raw_repo_root).is_absolute():
        raise OutcomeEvidenceRunnerError(
            "qualification registration repository root is invalid"
        )
    repo_root = _qualification_require_no_follow_path(
        raw_repo_root,
        "registered repository root",
        expected_kind="directory",
    )
    integrity = payload.get("integrity_rules")
    implementation_paths = (
        integrity.get("implementation_paths")
        if isinstance(integrity, Mapping)
        else None
    )
    if not isinstance(implementation_paths, list):
        raise OutcomeEvidenceRunnerError(
            "qualification registration implementation paths are invalid"
        )
    for relative_path in implementation_paths:
        if not isinstance(relative_path, str):
            raise OutcomeEvidenceRunnerError(
                "qualification registration implementation path is invalid"
            )
        _qualification_require_no_follow_path(
            repo_root / relative_path,
            f"implementation file {relative_path}",
            expected_kind="file",
        )
    return _require_launchable_runner_registration(
        _load_runner_registration(registration_path)
    )


def _qualification_no_follow_entries(
    root: Path,
    *,
    skip_root_git: bool = False,
    deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[tuple[Path, os.stat_result, bool]]:
    root = Path(root)
    try:
        root_metadata = root.lstat()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot inspect qualification filesystem root: {exc}"
        ) from exc
    if (
        _qualification_metadata_is_link_or_reparse(root_metadata)
        or not stat.S_ISDIR(root_metadata.st_mode)
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification filesystem root is not a regular directory"
        )
    pending = [root]
    entries = []
    while pending:
        if deadline is not None and monotonic() >= deadline:
            raise OutcomeEvidenceRunnerError(
                "qualification live source validation exceeded its release budget"
            )
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                children = sorted(iterator, key=lambda entry: entry.name)
        except OSError as exc:
            raise OutcomeEvidenceRunnerError(
                f"cannot inspect qualification source filesystem: {exc}"
            ) from exc
        for child in children:
            if skip_root_git and child.name == ".git" and directory == root:
                continue
            if deadline is not None and monotonic() >= deadline:
                raise OutcomeEvidenceRunnerError(
                    "qualification live source validation exceeded its release budget"
                )
            try:
                metadata = child.stat(follow_symlinks=False)
            except OSError as exc:
                raise OutcomeEvidenceRunnerError(
                    f"cannot inspect qualification source filesystem: {exc}"
                ) from exc
            path = Path(child.path)
            is_link_or_reparse = _qualification_metadata_is_link_or_reparse(
                metadata
            )
            entries.append((path, metadata, is_link_or_reparse))
            if stat.S_ISDIR(metadata.st_mode) and not is_link_or_reparse:
                pending.append(path)
    return sorted(entries, key=lambda row: str(row[0]))


def _qualification_validate_git_metadata(
    repo_root: Path,
    *,
    deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> Path:
    def require_budget() -> None:
        if deadline is not None and monotonic() >= deadline:
            raise OutcomeEvidenceRunnerError(
                "qualification live source validation exceeded its release budget"
            )

    require_budget()
    repo_root = _qualification_require_no_follow_path(
        repo_root,
        "Git repository root",
        expected_kind="directory",
    )
    git_root = _qualification_require_no_follow_path(
        repo_root / ".git",
        "Git metadata root",
        expected_kind="directory",
    )
    for path, _metadata, is_link_or_reparse in (
        _qualification_no_follow_entries(
            git_root,
            deadline=deadline,
            monotonic=monotonic,
        )
    ):
        if is_link_or_reparse:
            raise OutcomeEvidenceRunnerError(
                "qualification Git metadata contains a symbolic link or "
                f"reparse point: {path}"
            )
    grafts_path = git_root / "info" / "grafts"
    if _qualification_path_entry_exists(grafts_path):
        raise OutcomeEvidenceRunnerError(
            "qualification Git graft metadata is forbidden"
        )
    attributes_path = git_root / "info" / "attributes"
    if _qualification_path_entry_exists(attributes_path):
        raise OutcomeEvidenceRunnerError(
            "qualification Git info attributes are forbidden"
        )
    for relative_path in (
        "commondir",
        "objects/info/alternates",
        "objects/info/http-alternates",
    ):
        if _qualification_path_entry_exists(git_root / relative_path):
            raise OutcomeEvidenceRunnerError(
                "qualification Git metadata indirection is forbidden: "
                f"{relative_path}"
            )
    replace_path = git_root / "refs" / "replace"
    if _qualification_path_entry_exists(replace_path):
        raise OutcomeEvidenceRunnerError(
            "qualification Git replacement refs are forbidden"
        )
    packed_refs_path = git_root / "packed-refs"
    if _qualification_path_entry_exists(packed_refs_path):
        require_budget()
        packed_refs_path = _qualification_require_no_follow_path(
            packed_refs_path,
            "Git packed refs",
            expected_kind="file",
        )
        try:
            packed_refs = packed_refs_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OutcomeEvidenceRunnerError(
                f"cannot inspect qualification Git packed refs: {exc}"
            ) from exc
        require_budget()
        if any(
            line.partition(" ")[2].startswith("refs/replace/")
            for line in packed_refs.splitlines()
            if line and not line.startswith(("#", "^"))
        ):
            raise OutcomeEvidenceRunnerError(
                "qualification Git packed replacement refs are forbidden"
            )
    for config_name in ("config", "config.worktree"):
        config_path = git_root / config_name
        if not _qualification_path_entry_exists(config_path):
            continue
        config_path = _qualification_require_no_follow_path(
            config_path,
            f"Git repository {config_name}",
            expected_kind="file",
        )
        require_budget()
        try:
            config_text = config_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OutcomeEvidenceRunnerError(
                f"cannot inspect qualification Git config: {exc}"
            ) from exc
        require_budget()
        normalized_config = "".join(config_text.casefold().split())
        forbidden_config_tokens = (
            "[include",
            "fsmonitor",
            "hookspath",
            "external=",
            "filter",
            "clean=",
            "process=",
            "attributesfile",
            "textconv",
            "sshcommand",
            "partialclone",
            "promisor",
            "[protocol",
            "protocol.ext.allow",
            "ext::",
        )
        if any(
            token in normalized_config for token in forbidden_config_tokens
        ):
            raise OutcomeEvidenceRunnerError(
                "qualification Git repository config contains an unsafe "
                "execution directive"
            )
    return git_root


def _qualification_implementation_sha256(
    registration: OutcomeEvidenceRegistration,
) -> dict[str, str]:
    repo_root = _qualification_require_no_follow_path(
        registration.repo_root,
        "repository root",
        expected_kind="directory",
    )
    raw_paths = registration.to_record()["integrity_rules"]["implementation_paths"]
    result = {}
    for relative_path in raw_paths:
        path = _qualification_require_no_follow_path(
            repo_root / relative_path,
            f"implementation file {relative_path}",
            expected_kind="file",
        )
        if not path.is_relative_to(repo_root):
            raise OutcomeEvidenceRunnerError(
                f"qualification implementation file is invalid: {relative_path}"
            )
        result[relative_path] = _path_sha256(
            path,
            "qualification implementation file",
        )
    return result


def _qualification_git_source_output(
    repo_root: Path,
    *arguments: str,
    binary: bool = False,
    deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> str | bytes:
    git_root = _qualification_validate_git_metadata(
        repo_root,
        deadline=deadline,
        monotonic=monotonic,
    )
    timeout = None
    if deadline is not None:
        timeout = deadline - monotonic()
        if timeout <= 0:
            raise OutcomeEvidenceRunnerError(
                "qualification live source validation exceeded its release budget"
            )
    try:
        completed = subprocess.run(
            _qualification_git_command(*arguments),
            cwd=repo_root,
            capture_output=True,
            check=False,
            env=_qualification_git_environment(
                repo_root=Path(repo_root),
                git_root=git_root,
            ),
            text=not binary,
            encoding=None if binary else "utf-8",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot inspect qualification source: {exc}"
        ) from exc
    stderr = completed.stderr
    stderr_text = (
        stderr.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes)
        else str(stderr or "")
    ).strip()
    if completed.returncode != 0 or stderr_text:
        detail = stderr_text or f"exit code {completed.returncode}"
        raise OutcomeEvidenceRunnerError(
            f"cannot inspect qualification source: git {' '.join(arguments)}: "
            f"{detail}"
        )
    return completed.stdout


def _qualification_untracked_executable_paths(
    repo_root: Path,
    *,
    tracked_paths: set[str],
    deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[str]:
    executable_paths = []
    for path, metadata, is_link_or_reparse in _qualification_no_follow_entries(
        repo_root,
        skip_root_git=True,
        deadline=deadline,
        monotonic=monotonic,
    ):
        relative_path = path.relative_to(repo_root).as_posix()
        if relative_path in tracked_paths:
            continue
        if is_link_or_reparse or (
            stat.S_ISREG(metadata.st_mode)
            and _qualification_review_path_is_executable(relative_path)
        ):
            executable_paths.append(relative_path)
    return sorted(set(executable_paths))


def _tracked_source_commit(
    repo_root: Path,
    *,
    deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> str:
    repo_root = _qualification_require_no_follow_path(
        repo_root,
        "repository root",
        expected_kind="directory",
    )
    try:
        status = _qualification_git_source_output(
            repo_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
            deadline=deadline,
            monotonic=monotonic,
        )
        commit = str(
            _qualification_git_source_output(
                repo_root,
                "rev-parse",
                "HEAD",
                deadline=deadline,
                monotonic=monotonic,
            )
        ).strip().lower()
        tracked_raw = _qualification_git_source_output(
            repo_root,
            "ls-files",
            "-v",
            "-z",
            binary=True,
            deadline=deadline,
            monotonic=monotonic,
        )
    except OutcomeEvidenceRunnerError:
        raise
    if status:
        raise OutcomeEvidenceRunnerError(
            "qualification source has tracked changes"
        )
    if not _is_lower_hex(commit, _GIT_COMMIT_LENGTH):
        raise OutcomeEvidenceRunnerError(
            "qualification source commit is invalid"
        )
    if not isinstance(tracked_raw, bytes):
        raise OutcomeEvidenceRunnerError(
            "qualification tracked source inventory is invalid"
        )
    try:
        tracked_paths = set()
        for row in tracked_raw.split(b"\0"):
            if not row:
                continue
            if len(row) < 3 or row[1:2] != b" ":
                raise OutcomeEvidenceRunnerError(
                    "qualification tracked source index row is invalid"
                )
            status_tag = chr(row[0])
            if status_tag != "H":
                raise OutcomeEvidenceRunnerError(
                    "qualification tracked source has a forbidden index flag: "
                    f"{status_tag}"
                )
            tracked_paths.add(row[2:].decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise OutcomeEvidenceRunnerError(
            f"qualification tracked source path is not UTF-8: {exc}"
        ) from exc
    executable_untracked = _qualification_untracked_executable_paths(
        repo_root,
        tracked_paths=tracked_paths,
        deadline=deadline,
        monotonic=monotonic,
    )
    if executable_untracked:
        raise OutcomeEvidenceRunnerError(
            "qualification source has untracked executable paths: "
            + ", ".join(executable_untracked)
        )
    return commit


def _require_committed_qualification_registration(
    registration_path: Path,
    repo_root: Path,
    source_commit: str,
) -> None:
    resolved_root = _qualification_require_no_follow_path(
        repo_root,
        "repository root",
        expected_kind="directory",
    )
    resolved_registration = _qualification_require_no_follow_path(
        registration_path,
        "registration",
        expected_kind="file",
    )
    try:
        relative_path = resolved_registration.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification registration is outside the source repository"
        ) from exc
    try:
        _qualification_git_source_output(
            resolved_root,
            "ls-files",
            "--error-unmatch",
            "--",
            relative_path,
        )
        committed_bytes = _qualification_git_source_output(
            resolved_root,
            "show",
            f"{source_commit}:{relative_path}",
            binary=True,
        )
        current_bytes = resolved_registration.read_bytes()
    except (OSError, OutcomeEvidenceRunnerError) as exc:
        raise OutcomeEvidenceRunnerError(
            f"qualification registration is not committed: {exc}"
        ) from exc
    if current_bytes != committed_bytes:
        raise OutcomeEvidenceRunnerError(
            "qualification registration differs from the source commit"
        )


def _require_committed_qualification_request_source(
    request_source_path: Path,
    repo_root: Path,
    review_commit: str,
    expected_request_bytes: bytes,
) -> None:
    resolved_root = _qualification_require_no_follow_path(
        repo_root,
        "repository root",
        expected_kind="directory",
    )
    resolved_source = _qualification_require_no_follow_path(
        request_source_path,
        "request source",
        expected_kind="file",
    )
    try:
        relative_path = resolved_source.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification request source is outside the source repository"
        ) from exc
    try:
        _qualification_git_source_output(
            resolved_root,
            "ls-files",
            "--error-unmatch",
            "--",
            relative_path,
        )
        committed_bytes = _qualification_git_source_output(
            resolved_root,
            "show",
            f"{review_commit}:{relative_path}",
            binary=True,
        )
        current_bytes = resolved_source.read_bytes()
    except OutcomeEvidenceRunnerError:
        raise
    except (OSError, OutcomeEvidenceRunnerError) as exc:
        raise OutcomeEvidenceRunnerError(
            f"qualification request source is not committed: {exc}"
        ) from exc
    if (
        current_bytes != committed_bytes
        or current_bytes != expected_request_bytes
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification request source differs from the reviewed commit"
        )


def _qualification_committed_bytes(
    repo_root: Path,
    commit: str,
    relative_path: str,
    label: str,
) -> bytes:
    try:
        return _qualification_git_source_output(
            repo_root,
            "show",
            f"{commit}:{relative_path}",
            binary=True,
        )
    except (OSError, OutcomeEvidenceRunnerError) as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot read committed {label}: {exc}"
        ) from exc


def _validate_qualification_review_chain(
    *,
    request: Mapping[str, Any],
    request_source_path: Path,
    expected_request_bytes: bytes,
    expected_review_commit: Any,
    expected_request_file_sha256: Any,
    expected_request_size: Any,
    registration: OutcomeEvidenceRegistration,
    registration_path: Path,
    implementation_sha256: Any,
) -> dict[str, Any]:
    repo_root = _qualification_require_no_follow_path(
        registration.repo_root,
        "repository root",
        expected_kind="directory",
    )
    if not isinstance(expected_review_commit, str) or not _is_lower_hex(
        expected_review_commit,
        _GIT_COMMIT_LENGTH,
    ):
        raise OutcomeEvidenceRunnerError(
            "expected qualification review commit is invalid"
        )
    if not isinstance(expected_request_file_sha256, str) or not _is_lower_hex(
        expected_request_file_sha256,
        _SHA256_LENGTH,
    ):
        raise OutcomeEvidenceRunnerError(
            "expected qualification request file hash is invalid"
        )
    if type(expected_request_size) is not int or expected_request_size <= 0:
        raise OutcomeEvidenceRunnerError(
            "expected qualification request byte count is invalid"
        )
    observed_file_sha256 = hashlib.sha256(expected_request_bytes).hexdigest()
    if (
        observed_file_sha256 != expected_request_file_sha256
        or len(expected_request_bytes) != expected_request_size
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification request file binding differs from reviewed values"
        )
    review_head = _tracked_source_commit(repo_root)
    if review_head != expected_review_commit:
        raise OutcomeEvidenceRunnerError(
            "qualification launch HEAD differs from the reviewed commit"
        )
    source_commit = request["source_commit"]
    try:
        parent_row = str(
            _qualification_git_source_output(
                repo_root,
                "rev-list",
                "--parents",
                "-n",
                "1",
                expected_review_commit,
            )
        ).strip().lower().split()
        diff_paths = sorted(
            path
            for path in str(
                _qualification_git_source_output(
                    repo_root,
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--name-only",
                    "--no-renames",
                    source_commit,
                    expected_review_commit,
                )
            ).splitlines()
            if path
        )
    except (OSError, OutcomeEvidenceRunnerError) as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot verify qualification review commit: {exc}"
        ) from exc
    if parent_row != [expected_review_commit, source_commit]:
        raise OutcomeEvidenceRunnerError(
            "qualification review commit is not a direct child of the source commit"
        )
    if diff_paths != request["review_allowed_paths"]:
        raise OutcomeEvidenceRunnerError(
            "qualification review commit differs from the allowed path set"
        )
    _require_committed_qualification_request_source(
        request_source_path,
        repo_root,
        expected_review_commit,
        expected_request_bytes,
    )
    _require_committed_qualification_registration(
        registration_path,
        repo_root,
        source_commit,
    )
    try:
        registration_relative = registration_path.relative_to(
            repo_root
        ).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification registration is outside the source repository"
        ) from exc
    registration_bytes = registration_path.read_bytes()
    for commit in {expected_review_commit}:
        if _qualification_committed_bytes(
            repo_root,
            commit,
            registration_relative,
            "qualification registration",
        ) != registration_bytes:
            raise OutcomeEvidenceRunnerError(
                "qualification registration changed after the source commit"
            )

    relative_paths = registration.to_record()["integrity_rules"][
        "implementation_paths"
    ]
    if not isinstance(implementation_sha256, Mapping) or set(
        implementation_sha256
    ) != set(relative_paths):
        raise OutcomeEvidenceRunnerError(
            "qualification implementation binding is invalid"
        )
    for relative_path in relative_paths:
        current_path = _qualification_require_no_follow_path(
            repo_root / relative_path,
            f"implementation file {relative_path}",
            expected_kind="file",
        )
        if not current_path.is_relative_to(repo_root):
            raise OutcomeEvidenceRunnerError(
                f"qualification implementation file is invalid: {relative_path}"
            )
        try:
            current_bytes = current_path.read_bytes()
        except OSError as exc:
            raise OutcomeEvidenceRunnerError(
                f"cannot read qualification implementation file: {exc}"
            ) from exc
        expected_hash = implementation_sha256[relative_path]
        if (
            not isinstance(expected_hash, str)
            or not _is_lower_hex(expected_hash, _SHA256_LENGTH)
            or hashlib.sha256(current_bytes).hexdigest() != expected_hash
        ):
            raise OutcomeEvidenceRunnerError(
                f"qualification implementation hash mismatch: {relative_path}"
            )
        for commit in {source_commit, expected_review_commit}:
            if _qualification_committed_bytes(
                repo_root,
                commit,
                relative_path,
                f"qualification implementation {relative_path}",
            ) != current_bytes:
                raise OutcomeEvidenceRunnerError(
                    "qualification implementation changed across review: "
                    f"{relative_path}"
                )
    return _build_qualification_review_binding(
        request=request,
        review_commit=expected_review_commit,
        request_source_path=request_source_path,
        request_source_relative=request_source_path.relative_to(
            repo_root
        ).as_posix(),
        request_bytes=expected_request_bytes,
    )


def _build_qualification_review_binding(
    *,
    request: Mapping[str, Any],
    review_commit: str,
    request_source_path: Path,
    request_source_relative: str,
    request_bytes: bytes,
) -> dict[str, Any]:
    file_sha256 = hashlib.sha256(request_bytes).hexdigest()
    implementation_map_sha256 = hashlib.sha256(
        _canonical_json(request["implementation_sha256"]).encode("utf-8")
    ).hexdigest()
    record = {
        "active_request": {
            "file_sha256": file_sha256,
            "path": request["request_path"],
            "request_hash": request["request_hash"],
            "size": len(request_bytes),
        },
        "allowed_review_paths": list(request["review_allowed_paths"]),
        "implementation_map_sha256": implementation_map_sha256,
        "registration": dict(request["registration"]),
        "request_source": {
            "file_sha256": file_sha256,
            "path": str(request_source_path),
            "relative_path": request_source_relative,
            "request_hash": request["request_hash"],
            "size": len(request_bytes),
        },
        "review_binding_hash": None,
        "review_commit": review_commit,
        "schema_version": QUALIFICATION_REVIEW_BINDING_SCHEMA_VERSION,
        "source_commit": request["source_commit"],
    }
    record["review_binding_hash"] = _self_hash(
        record,
        "review_binding_hash",
    )
    return json.loads(_canonical_json(record))


def _validate_qualification_live_review_boundaries(
    *,
    request: Mapping[str, Any],
    registration: OutcomeEvidenceRegistration,
    review_binding: Mapping[str, Any],
    deadline: float,
    monotonic: Callable[[], float],
) -> None:
    repo_root = _qualification_require_no_follow_path(
        registration.repo_root,
        "repository root",
        expected_kind="directory",
    )
    review_commit = review_binding["review_commit"]
    observed_head = _tracked_source_commit(
        repo_root,
        deadline=deadline,
        monotonic=monotonic,
    )
    if observed_head != review_commit:
        raise OutcomeEvidenceRunnerError(
            "qualification launch HEAD changed before release"
        )
    request_source_path = _qualification_require_no_follow_path(
        request["request_source_path"],
        "request source",
        expected_kind="file",
    )
    try:
        request_source_bytes = request_source_path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot reread qualification request source: {exc}"
        ) from exc
    expected_request_bytes = (_canonical_json(request) + "\n").encode("utf-8")
    if request_source_bytes != expected_request_bytes:
        raise OutcomeEvidenceRunnerError(
            "qualification request source changed before release"
        )
    registration_path = _qualification_require_no_follow_path(
        request["registration"]["path"],
        "registration",
        expected_kind="file",
    )
    if request["registration"]["file_sha256"] != _path_sha256(
        registration_path,
        "qualification registration",
        deadline=deadline,
        monotonic=monotonic,
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification registration changed before release"
        )
    for relative_path, expected_hash in request["implementation_sha256"].items():
        if deadline is not None and monotonic() >= deadline:
            raise OutcomeEvidenceRunnerError(
                "qualification live source validation exceeded its release budget"
            )
        implementation_path = _qualification_require_no_follow_path(
            repo_root / relative_path,
            f"implementation file {relative_path}",
            expected_kind="file",
        )
        if _path_sha256(
            implementation_path,
            f"qualification implementation {relative_path}",
            deadline=deadline,
            monotonic=monotonic,
        ) != expected_hash:
            raise OutcomeEvidenceRunnerError(
                "qualification implementation changed before release: "
                f"{relative_path}"
            )
    try:
        request_source_relative = request_source_path.relative_to(
            repo_root
        ).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceRunnerError(
            "qualification request source left the source repository"
        ) from exc
    observed_binding = _build_qualification_review_binding(
        request=request,
        review_commit=review_commit,
        request_source_path=request_source_path,
        request_source_relative=request_source_relative,
        request_bytes=request_source_bytes,
    )
    if observed_binding != dict(review_binding):
        raise OutcomeEvidenceRunnerError(
            "qualification review binding changed before release"
        )
    if monotonic() >= deadline:
        raise OutcomeEvidenceRunnerError(
            "qualification live source validation exceeded its release budget"
        )


def _qualification_release_validation_deadline(
    *,
    ready_created_unix_ns: int,
    observed_unix_ns: int,
    release_timeout_seconds: int,
    monotonic_now: float,
) -> float:
    elapsed_seconds = max(
        0.0,
        (observed_unix_ns - ready_created_unix_ns) / 1_000_000_000,
    )
    remaining_seconds = release_timeout_seconds - elapsed_seconds
    validation_budget = min(5.0, remaining_seconds)
    if validation_budget <= 0:
        raise OutcomeEvidenceRunnerError(
            "qualification live source validation exceeded its release budget"
        )
    return monotonic_now + validation_budget


def _require_qualification_release_validation_budget(
    deadline: float,
    monotonic: Callable[[], float],
) -> None:
    if monotonic() >= deadline:
        raise OutcomeEvidenceRunnerError(
            "qualification live source validation exceeded its release budget"
        )


def _validate_qualification_id(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value[0] not in "abcdefghijklmnopqrstuvwxyz0123456789"
        or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-"
            for character in value
        )
    ):
        raise OutcomeEvidenceRunnerError("qualification_id is invalid")
    return value


def _resolved_absolute_path(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise OutcomeEvidenceRunnerError(f"{field} must be nonempty")
    path = Path(value)
    lexical_path = Path(os.path.abspath(path))
    if not path.is_absolute() or str(lexical_path) != value:
        raise OutcomeEvidenceRunnerError(f"{field} must be resolved absolute")
    return lexical_path


def _path_sha256(
    path: Path,
    label: str,
    *,
    deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> str:
    def require_budget() -> None:
        if deadline is not None and monotonic() >= deadline:
            raise OutcomeEvidenceRunnerError(
                "qualification live source validation exceeded its release budget"
            )

    try:
        digest = hashlib.sha256()
        with Path(path).open("rb") as source:
            while True:
                require_budget()
                block = source.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
        require_budget()
        return digest.hexdigest()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(f"cannot read {label}: {exc}") from exc


def _self_hash(record: Mapping[str, Any], field: str) -> str:
    if field not in record:
        raise OutcomeEvidenceRunnerError(f"self-hash field is missing: {field}")
    payload = dict(record)
    payload[field] = None
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def execute_prelock_qualification(
    *,
    registration_path: Path | str,
    request_path: Path | str,
    expected_request_hash: str,
    expected_review_commit: str,
    expected_request_file_sha256: str,
    expected_request_size: int,
    process_starter: Callable[[Sequence[str], Mapping[str, str]], Any],
    qualification_launch_command: Sequence[str] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    time_ns: Callable[[], int] = time.time_ns,
) -> dict[str, Any]:
    """Run one request-bound child through release without study state."""

    if not callable(process_starter):
        raise OutcomeEvidenceRunnerError("qualification process_starter must be callable")
    request = load_qualification_request_source(
        request_path,
        registration_path=registration_path,
        expected_request_hash=expected_request_hash,
        expected_review_commit=expected_review_commit,
        expected_request_file_sha256=expected_request_file_sha256,
        expected_request_size=expected_request_size,
    )
    if _QUALIFICATION_CLI_REQUESTED:
        runner_anchor = os.environ.get(QUALIFICATION_RUNNER_SHA256_ENV)
        expected_runner_anchor = request["implementation_sha256"].get(
            QUALIFICATION_RUNNER_RELATIVE_PATH
        )
        if (
            not isinstance(expected_runner_anchor, str)
            or runner_anchor != expected_runner_anchor
        ):
            raise OutcomeEvidenceRunnerError(
                "qualification trusted launcher anchor does not match the "
                "reviewed runner implementation"
            )
    request_source_path = _qualification_require_no_follow_path(
        request["request_source_path"],
        "request source",
        expected_kind="file",
    )
    request_source_bytes = request_source_path.read_bytes()
    resolved_registration_path = _qualification_require_no_follow_path(
        registration_path,
        "registration",
        expected_kind="file",
    )
    registration = _load_qualification_registration(
        resolved_registration_path
    )
    review_binding = _validate_qualification_review_chain(
        request=request,
        request_source_path=request_source_path,
        expected_request_bytes=request_source_bytes,
        expected_review_commit=expected_review_commit,
        expected_request_file_sha256=expected_request_file_sha256,
        expected_request_size=expected_request_size,
        registration=registration,
        registration_path=resolved_registration_path,
        implementation_sha256=request["implementation_sha256"],
    )
    active_request_path = Path(request["request_path"])
    started_unix_ns = request["created_unix_ns"]
    process = None
    child_pid = None
    exit_code = None
    launch_count = 0
    request_consumed = False
    stage = "prelaunch_validation"
    try:
        _qualification_validate_prelaunch_isolation(
            request,
            qualification_launch_command,
        )
        stage = "publish_request"
        _publish_text_once(
            active_request_path,
            _canonical_json(request) + "\n",
            "qualification request",
        )
        request_consumed = True
        request = load_qualification_request(
            active_request_path,
            registration_path=registration_path,
        )
        handshake = request["handshake"]
        paths = HandshakePaths(
            attempt=Path(handshake["attempt_path"]),
            ready=Path(handshake["ready_path"]),
            release=Path(handshake["release_path"]),
        )
        stage = "build_attempt"
        started_unix_ns = _positive_time_ns(time_ns)
        attempt = build_attempt_record(
            study_id=request["qualification_id"],
            registration_hash=request["registration"]["canonical_hash"],
            run_lock_hash=handshake["run_lock_hash"],
            slot_number=handshake["slot_number"],
            session_id=handshake["session_id"],
            config_path=Path(request["config"]["path"]),
            config_sha256=request["config"]["sha256"],
            marker_start_count=request["marker"]["start_count"],
            paths=paths,
            readiness_timeout_seconds=handshake["readiness_timeout_seconds"],
            release_timeout_seconds=handshake["release_timeout_seconds"],
            created_unix_ns=started_unix_ns,
        )
        stage = "publish_attempt"
        publish_record_once(paths.attempt, attempt)
        stage = "start_child"
        child_environment = _qualification_child_environment(
            config_path=request["config"]["path"],
            attempt_path=str(paths.attempt),
            attempt_hash=attempt["attempt_hash"],
        )
        launch_count = 1
        process = process_starter(
            tuple(request["child_command"]),
            MappingProxyType(child_environment),
        )
        child_pid = _child_process_pid(process)
        stage = "wait_for_ready"
        ready = _wait_for_child_readiness(
            process=process,
            child_pid=child_pid,
            attempt=attempt,
            ready_path=paths.ready,
            ready_path_validator=lambda path: (
                _qualification_require_no_follow_path(
                    path,
                    "ready artifact",
                    expected_kind="file",
                )
            ),
            timeout_seconds=handshake["readiness_timeout_seconds"],
            monotonic=monotonic,
            sleep=sleep,
        )
        stage = "pre_release_validation"
        release_validation_deadline = _qualification_release_validation_deadline(
            ready_created_unix_ns=ready["created_unix_ns"],
            observed_unix_ns=_positive_time_ns(time_ns),
            release_timeout_seconds=handshake["release_timeout_seconds"],
            monotonic_now=monotonic(),
        )
        _validate_qualification_runtime_boundaries(
            request=request,
            registration=registration,
            attempt=attempt,
            review_binding=review_binding,
            release_allowed=False,
            release_validation_deadline=release_validation_deadline,
            monotonic=monotonic,
        )
        _require_child_running(process, stage="qualification release")
        _require_qualification_release_validation_budget(
            release_validation_deadline,
            monotonic,
        )
        stage = "publish_release"
        release = build_release_record(
            attempt,
            ready,
            created_unix_ns=_positive_time_ns(time_ns),
        )
        publish_record_once(paths.release, release)
        stage = "wait_for_qualification_exit"
        try:
            exit_code = process.wait(
                timeout=handshake["release_timeout_seconds"]
            )
        except subprocess.TimeoutExpired as exc:
            raise OutcomeEvidenceRunnerError(
                "qualification child did not exit within "
                f"{handshake['release_timeout_seconds']} seconds"
            ) from exc
        if type(exit_code) is not int:
            raise OutcomeEvidenceRunnerError(
                "qualification child returned a non-integer exit code"
            )
        if exit_code != 0:
            raise OutcomeEvidenceRunnerError(
                f"qualification child exited with code {exit_code}"
            )
        stage = "post_exit_validation"
        _validate_qualification_runtime_boundaries(
            request=request,
            registration=registration,
            attempt=attempt,
            review_binding=review_binding,
            release_allowed=True,
        )
        stage = "restore_isolation"
        isolation_evidence = _qualification_finalize_isolation(
            request,
            process,
        )
        if not isolation_evidence["matched"]:
            raise OutcomeEvidenceRunnerError(
                "qualification post isolation mismatch: "
                + ", ".join(isolation_evidence["mismatches"])
            )
        stage = "post_exit_validation"
        ended_unix_ns = _positive_time_ns(time_ns)
        result = _build_qualification_result(
            request=request,
            review_binding=review_binding,
            status="passed",
            started_unix_ns=started_unix_ns,
            ended_unix_ns=ended_unix_ns,
            launch_count=launch_count,
            child_pid=child_pid,
            exit_code=exit_code,
            cleanup_attempted=False,
            cleanup_error=None,
            failure=None,
            isolation=isolation_evidence,
        )
        stage = "publish_completion"
        _require_paths_absent(
            (Path(request["failure_path"]),),
            "qualification failure terminal exists before completion",
        )
        publish_qualification_result_once(
            Path(request["completion_path"]),
            result,
        )
        return result
    except BaseException as exc:
        cleanup_attempted = _child_cleanup_required(process)
        cleanup_error = _terminate_child_process(process)
        isolation_evidence = _qualification_finalize_isolation(
            request,
            process,
        )
        if not isinstance(exc, Exception):
            raise
        if exit_code is None:
            exit_code = _safe_process_exit_code(process)
        ended_unix_ns = _safe_time_ns(time_ns)
        if ended_unix_ns is None:
            ended_unix_ns = started_unix_ns
        failure = {
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "stage": stage,
        }
        if not request_consumed:
            suffix = (
                f"; child cleanup failed: {cleanup_error}"
                if cleanup_error is not None
                else ""
            )
            raise OutcomeEvidenceRunnerError(
                f"{stage}: {type(exc).__name__}: {exc}{suffix}"
            ) from exc
        if stage == "publish_completion":
            suffix = (
                f"; child cleanup failed: {cleanup_error}"
                if cleanup_error is not None
                else ""
            )
            raise OutcomeEvidenceRunnerError(
                "publish_completion: completion publication failed; "
                "the consumed evidence remains partial and must be sealed "
                f"without a failure relabel{suffix}"
            ) from exc
        if stage == "post_exit_validation":
            suffix = (
                f"; child cleanup failed: {cleanup_error}"
                if cleanup_error is not None
                else ""
            )
            raise OutcomeEvidenceRunnerError(
                "post_exit_validation: post-exit validation failed; "
                "the consumed release evidence remains partial and must be "
                f"sealed without a failure relabel{suffix}"
            ) from exc
        try:
            result = _build_qualification_result(
                request=request,
                review_binding=review_binding,
                status="failed",
                started_unix_ns=started_unix_ns,
                ended_unix_ns=ended_unix_ns,
                launch_count=launch_count,
                child_pid=child_pid,
                exit_code=exit_code,
                cleanup_attempted=cleanup_attempted,
                cleanup_error=cleanup_error,
                failure=failure,
                isolation=isolation_evidence,
            )
            _require_paths_absent(
                (Path(request["completion_path"]),),
                "qualification completion terminal exists before failure",
            )
            publish_qualification_result_once(
                Path(request["failure_path"]),
                result,
            )
        except BaseException as result_exc:
            raise OutcomeEvidenceRunnerError(
                f"{stage}: {type(exc).__name__}: {exc}; "
                "qualification failure publication failed: "
                f"{type(result_exc).__name__}: {result_exc}"
            ) from exc
        suffix = (
            f"; child cleanup failed: {cleanup_error}"
            if cleanup_error is not None
            else ""
        )
        raise OutcomeEvidenceRunnerError(
            f"{stage}: {type(exc).__name__}: {exc}{suffix}"
        ) from exc


def publish_qualification_result_once(
    path: Path | str,
    result: Mapping[str, Any],
) -> None:
    validated = _validate_qualification_result(dict(result))
    _publish_text_once(
        Path(os.path.abspath(os.fspath(path))),
        _canonical_json(validated) + "\n",
        "qualification result",
    )


def _build_qualification_result(
    *,
    request: Mapping[str, Any],
    review_binding: Mapping[str, Any],
    status: str,
    started_unix_ns: int,
    ended_unix_ns: int,
    launch_count: int,
    child_pid: int | None,
    exit_code: int | None,
    cleanup_attempted: bool,
    cleanup_error: str | None,
    failure: Mapping[str, Any] | None,
    isolation: Mapping[str, Any],
) -> dict[str, Any]:
    handshake = request["handshake"]
    marker_end_count = _safe_marker_count(Path(request["marker"]["path"]))
    record = {
        "authority": {
            "causal_claim": False,
            "collection": False,
            "gameplay_policy_change": False,
            "run_lock": False,
            "study_start": False,
            "training": False,
        },
        "child_command": list(request["child_command"]),
        "config": dict(request["config"]),
        "created_unix_ns": started_unix_ns,
        "ended_unix_ns": ended_unix_ns,
        "failure": None if failure is None else dict(failure),
        "forbidden_paths": {
            path: _qualification_path_entry_exists(Path(path))
            for path in request["forbidden_paths"]
        },
        "handshake": {
            name: {
                "path": handshake[f"{name}_path"],
                "sha256": _optional_path_sha256(Path(handshake[f"{name}_path"])),
            }
            for name in ("attempt", "ready", "release")
        },
        "implementation_sha256": dict(request["implementation_sha256"]),
        "isolation": dict(isolation),
        "marker": {
            "end_count": marker_end_count,
            "path": request["marker"]["path"],
            "start_count": request["marker"]["start_count"],
        },
        "process": {
            "cleanup_attempted": cleanup_attempted,
            "cleanup_error": cleanup_error,
            "exit_code": exit_code,
            "launch_count": launch_count,
            "pid": child_pid,
        },
        "registration": dict(request["registration"]),
        "request": {
            "hash": request["request_hash"],
            "path": request["request_path"],
        },
        "review_binding": dict(review_binding),
        "result_hash": None,
        "schema_version": QUALIFICATION_RESULT_SCHEMA_VERSION,
        "source_commit": request["source_commit"],
        "status": status,
    }
    record["result_hash"] = _self_hash(record, "result_hash")
    return _validate_qualification_result(record)


def _validate_qualification_result_isolation(value: Any) -> dict[str, Any]:
    expected_fields = {
        "baseline_hash",
        "child_alive",
        "communication_restored",
        "matched",
        "mismatches",
        "observation_error",
        "post_observation",
        "post_observation_hash",
        "restoration_error",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation fields mismatch"
        )
    record = dict(value)
    if not isinstance(record["baseline_hash"], str) or not _is_lower_hex(
        record["baseline_hash"],
        _SHA256_LENGTH,
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation baseline hash is invalid"
        )
    if record["child_alive"] is not None and type(record["child_alive"]) is not bool:
        raise OutcomeEvidenceRunnerError(
            "qualification result child liveness is invalid"
        )
    for field in ("communication_restored", "matched"):
        if type(record[field]) is not bool:
            raise OutcomeEvidenceRunnerError(
                f"qualification result isolation {field} flag is invalid"
            )
    mismatches = record["mismatches"]
    if (
        isinstance(mismatches, (str, bytes))
        or not isinstance(mismatches, Sequence)
        or list(mismatches) != sorted(set(mismatches))
        or any(not isinstance(item, str) or not item for item in mismatches)
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation mismatches are invalid"
        )
    for field in ("observation_error", "restoration_error"):
        error = record[field]
        if error is not None and (not isinstance(error, str) or not error):
            raise OutcomeEvidenceRunnerError(
                f"qualification result isolation {field} is invalid"
            )
    post_observation = record["post_observation"]
    post_hash = record["post_observation_hash"]
    if post_observation is None:
        if post_hash is not None:
            raise OutcomeEvidenceRunnerError(
                "qualification result absent post-observation has a hash"
            )
    elif (
        not isinstance(post_observation, Mapping)
        or not isinstance(post_hash, str)
        or not _is_lower_hex(post_hash, _SHA256_LENGTH)
        or post_observation.get("observation_hash") != post_hash
        or post_hash != _self_hash(post_observation, "observation_hash")
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification result post-observation hash is invalid"
        )
    mismatch_set = set(mismatches)
    observation_error = record["observation_error"]
    restoration_error = record["restoration_error"]
    if (observation_error is None) != (post_observation is not None) or (
        ("observation_error" in mismatch_set) != (observation_error is not None)
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation observation evidence contradicts"
        )
    if (restoration_error is None) != record["communication_restored"] or (
        ("communication_restore" in mismatch_set)
        != (record["communication_restored"] is False)
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation restoration evidence contradicts"
        )
    if ("child_process" in mismatch_set) != (
        record["child_alive"] is not False
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation child evidence contradicts"
        )
    expected_matched = (
        record["child_alive"] is False
        and record["communication_restored"] is True
        and not mismatches
        and observation_error is None
        and restoration_error is None
        and post_observation is not None
    )
    if record["matched"] is not expected_matched:
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation matched flag contradicts evidence"
        )
    return json.loads(_canonical_json(record))


def _validate_qualification_result(record: Mapping[str, Any]) -> dict[str, Any]:
    expected_fields = {
        "authority",
        "child_command",
        "config",
        "created_unix_ns",
        "ended_unix_ns",
        "failure",
        "forbidden_paths",
        "handshake",
        "implementation_sha256",
        "isolation",
        "marker",
        "process",
        "registration",
        "request",
        "review_binding",
        "result_hash",
        "schema_version",
        "source_commit",
        "status",
    }
    if not isinstance(record, Mapping) or set(record) != expected_fields:
        raise OutcomeEvidenceRunnerError("qualification result fields mismatch")
    if record["schema_version"] != QUALIFICATION_RESULT_SCHEMA_VERSION:
        raise OutcomeEvidenceRunnerError("qualification result schema mismatch")
    status = record["status"]
    if status not in {"passed", "failed"}:
        raise OutcomeEvidenceRunnerError("qualification result status is invalid")
    created = _timestamp(record["created_unix_ns"])
    ended = _timestamp(record["ended_unix_ns"])
    if ended < created:
        raise OutcomeEvidenceRunnerError("qualification result timestamps regress")
    supplied_hash = record["result_hash"]
    if not isinstance(supplied_hash, str) or not _is_lower_hex(
        supplied_hash,
        _SHA256_LENGTH,
    ):
        raise OutcomeEvidenceRunnerError("qualification result hash is invalid")
    if supplied_hash != _self_hash(record, "result_hash"):
        raise OutcomeEvidenceRunnerError("qualification result hash mismatch")
    _validate_qualification_review_binding(record["review_binding"])
    isolation = _validate_qualification_result_isolation(record["isolation"])
    authority = record["authority"]
    expected_authority_fields = {
        "causal_claim",
        "collection",
        "gameplay_policy_change",
        "run_lock",
        "study_start",
        "training",
    }
    if (
        not isinstance(authority, Mapping)
        or set(authority) != expected_authority_fields
        or any(
            type(value) is not bool or value is not False
            for value in authority.values()
        )
    ):
        raise OutcomeEvidenceRunnerError("qualification authority must be false")
    process = record["process"]
    if not isinstance(process, Mapping) or set(process) != {
        "cleanup_attempted",
        "cleanup_error",
        "exit_code",
        "launch_count",
        "pid",
    }:
        raise OutcomeEvidenceRunnerError("qualification process evidence is invalid")
    launch_count = process["launch_count"]
    if type(launch_count) is not int or launch_count not in {0, 1}:
        raise OutcomeEvidenceRunnerError("qualification launch count is invalid")
    pid = process["pid"]
    if pid is not None and (type(pid) is not int or pid <= 0):
        raise OutcomeEvidenceRunnerError("qualification child PID is invalid")
    exit_code = process["exit_code"]
    if exit_code is not None and type(exit_code) is not int:
        raise OutcomeEvidenceRunnerError("qualification exit code is invalid")
    if type(process["cleanup_attempted"]) is not bool:
        raise OutcomeEvidenceRunnerError("qualification cleanup flag is invalid")
    cleanup_error = process["cleanup_error"]
    if cleanup_error is not None and (
        not isinstance(cleanup_error, str) or not cleanup_error
    ):
        raise OutcomeEvidenceRunnerError("qualification cleanup error is invalid")
    handshake = record["handshake"]
    if not isinstance(handshake, Mapping) or set(handshake) != {
        "attempt",
        "ready",
        "release",
    }:
        raise OutcomeEvidenceRunnerError("qualification handshake evidence is invalid")
    for name in ("attempt", "ready", "release"):
        binding = handshake[name]
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise OutcomeEvidenceRunnerError(
                f"qualification {name} evidence is invalid"
            )
        _resolved_absolute_path(binding["path"], f"qualification {name} path")
        sha256 = binding["sha256"]
        if sha256 is not None and (
            not isinstance(sha256, str)
            or not _is_lower_hex(sha256, _SHA256_LENGTH)
        ):
            raise OutcomeEvidenceRunnerError(
                f"qualification {name} hash is invalid"
            )
    attempt_hash = handshake["attempt"]["sha256"]
    ready_hash = handshake["ready"]["sha256"]
    release_hash = handshake["release"]["sha256"]
    if launch_count == 1 and attempt_hash is None:
        raise OutcomeEvidenceRunnerError(
            "qualification launched child lacks attempt evidence"
        )
    if launch_count == 0 and any(
        (
            pid is not None,
            exit_code is not None,
            process["cleanup_attempted"],
            cleanup_error is not None,
            ready_hash is not None,
            release_hash is not None,
        )
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification process evidence contradicts launch count"
        )
    if ready_hash is not None and (
        launch_count != 1 or pid is None or attempt_hash is None
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification ready evidence requires one launched child"
        )
    if release_hash is not None and ready_hash is None:
        raise OutcomeEvidenceRunnerError(
            "qualification release evidence lacks ready evidence"
        )
    marker = record["marker"]
    if not isinstance(marker, Mapping) or set(marker) != {
        "end_count",
        "path",
        "start_count",
    }:
        raise OutcomeEvidenceRunnerError("qualification marker evidence is invalid")
    _resolved_absolute_path(marker["path"], "qualification marker result path")
    for field in ("start_count", "end_count"):
        value = marker[field]
        if value is not None and (type(value) is not int or value < 0):
            raise OutcomeEvidenceRunnerError(
                f"qualification marker {field} is invalid"
            )
    forbidden = record["forbidden_paths"]
    if not isinstance(forbidden, Mapping) or any(
        not isinstance(path, str) or type(exists) is not bool
        for path, exists in forbidden.items()
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification forbidden-path evidence is invalid"
        )
    _validate_qualification_result_lifecycle(record)
    success_evidence_complete = (
        launch_count == 1
        and pid is not None
        and exit_code == 0
        and process["cleanup_attempted"] is False
        and cleanup_error is None
        and marker["end_count"] == marker["start_count"]
        and not any(forbidden.values())
        and all(handshake[name]["sha256"] is not None for name in handshake)
        and isolation["matched"] is True
        and isolation["communication_restored"] is True
        and isolation["child_alive"] is False
        and isolation["mismatches"] == []
        and isolation["observation_error"] is None
        and isolation["restoration_error"] is None
        and isolation["post_observation"] is not None
    )
    if status == "passed":
        if record["failure"] is not None or not success_evidence_complete:
            raise OutcomeEvidenceRunnerError(
                "qualification passed result contradicts evidence"
            )
    else:
        failure = record["failure"]
        if not isinstance(failure, Mapping) or set(failure) != {
            "exception_type",
            "message",
            "stage",
        }:
            raise OutcomeEvidenceRunnerError(
                "qualification failed result lacks failure evidence"
            )
        if any(not isinstance(value, str) or not value for value in failure.values()):
            raise OutcomeEvidenceRunnerError(
                "qualification failure evidence is invalid"
            )
        if success_evidence_complete:
            raise OutcomeEvidenceRunnerError(
                "qualification failed result does not contradict success evidence"
            )
    return json.loads(_canonical_json(record))


def _validate_qualification_review_binding(value: Any) -> dict[str, Any]:
    expected_fields = {
        "active_request",
        "allowed_review_paths",
        "implementation_map_sha256",
        "registration",
        "request_source",
        "review_binding_hash",
        "review_commit",
        "schema_version",
        "source_commit",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise OutcomeEvidenceRunnerError(
            "qualification review binding fields mismatch"
        )
    if value["schema_version"] != QUALIFICATION_REVIEW_BINDING_SCHEMA_VERSION:
        raise OutcomeEvidenceRunnerError(
            "qualification review binding schema mismatch"
        )
    for field in ("source_commit", "review_commit"):
        if not isinstance(value[field], str) or not _is_lower_hex(
            value[field],
            _GIT_COMMIT_LENGTH,
        ):
            raise OutcomeEvidenceRunnerError(
                f"qualification review binding {field} is invalid"
            )
    for field in ("implementation_map_sha256", "review_binding_hash"):
        if not isinstance(value[field], str) or not _is_lower_hex(
            value[field],
            _SHA256_LENGTH,
        ):
            raise OutcomeEvidenceRunnerError(
                f"qualification review binding {field} is invalid"
            )
    if value["review_binding_hash"] != _self_hash(
        value,
        "review_binding_hash",
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification review binding hash mismatch"
        )
    allowed = value["allowed_review_paths"]
    if (
        isinstance(allowed, (str, bytes))
        or not isinstance(allowed, Sequence)
        or list(allowed) != sorted(set(allowed))
        or any(not isinstance(path, str) or not path for path in allowed)
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification review binding path set is invalid"
        )
    source = value["request_source"]
    active = value["active_request"]
    if not isinstance(source, Mapping) or set(source) != {
        "file_sha256",
        "path",
        "relative_path",
        "request_hash",
        "size",
    }:
        raise OutcomeEvidenceRunnerError(
            "qualification request-source review binding is invalid"
        )
    if not isinstance(active, Mapping) or set(active) != {
        "file_sha256",
        "path",
        "request_hash",
        "size",
    }:
        raise OutcomeEvidenceRunnerError(
            "qualification active-request review binding is invalid"
        )
    _resolved_absolute_path(source["path"], "reviewed request source path")
    _resolved_absolute_path(active["path"], "active request review path")
    for binding in (source, active):
        if (
            not isinstance(binding["file_sha256"], str)
            or not _is_lower_hex(binding["file_sha256"], _SHA256_LENGTH)
            or not isinstance(binding["request_hash"], str)
            or not _is_lower_hex(binding["request_hash"], _SHA256_LENGTH)
            or type(binding["size"]) is not int
            or binding["size"] <= 0
        ):
            raise OutcomeEvidenceRunnerError(
                "qualification request review file binding is invalid"
            )
    if (
        source["file_sha256"] != active["file_sha256"]
        or source["request_hash"] != active["request_hash"]
        or source["size"] != active["size"]
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification source/active request review binding differs"
        )
    if not isinstance(value["registration"], Mapping):
        raise OutcomeEvidenceRunnerError(
            "qualification registration review binding is invalid"
        )
    return json.loads(_canonical_json(value))


def _validate_qualification_result_lifecycle(
    record: Mapping[str, Any],
) -> None:
    request_binding = record["request"]
    if not isinstance(request_binding, Mapping) or set(request_binding) != {
        "hash",
        "path",
    }:
        raise OutcomeEvidenceRunnerError(
            "qualification result request binding is invalid"
        )
    request_path = _resolved_absolute_path(
        request_binding["path"],
        "qualification result request path",
    )
    request_path = _qualification_require_no_follow_path(
        request_path,
        "active request",
        expected_kind="file",
    )
    try:
        raw_request = request_path.read_bytes()
        request = json.loads(
            raw_request.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except OutcomeEvidenceRunnerError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot replay qualification result request: {exc}"
        ) from exc
    if (
        not isinstance(request, Mapping)
        or raw_request != (_canonical_json(request) + "\n").encode("utf-8")
        or request.get("request_hash") != request_binding["hash"]
        or request.get("request_hash") != _self_hash(request, "request_hash")
        or request.get("request_path") != str(request_path)
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification result request binding mismatch"
        )
    if request.get("schema_version") != QUALIFICATION_REQUEST_SCHEMA_VERSION:
        raise OutcomeEvidenceRunnerError(
            "qualification result requires a v2 request"
        )
    registration = _load_qualification_registration(
        request["registration"]["path"]
    )
    baseline = _validate_qualification_isolation_baseline(
        request.get("isolation"),
        registration=registration,
        marker_path=Path(request["marker"]["path"]),
        marker_start_count=request["marker"]["start_count"],
    )
    isolation = _validate_qualification_result_isolation(record["isolation"])
    if isolation["baseline_hash"] != baseline["baseline_hash"]:
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation baseline binding mismatch"
        )
    post_observation = isolation["post_observation"]
    if post_observation is not None:
        post_observation = _validate_qualification_isolation_observation(
            post_observation,
            baseline,
        )
        if post_observation["observation_hash"] != isolation[
            "post_observation_hash"
        ]:
            raise OutcomeEvidenceRunnerError(
                "qualification result post-observation binding mismatch"
            )
    expected_isolation_mismatches = []
    if post_observation is not None:
        expected_isolation_mismatches.extend(
            _qualification_isolation_mismatches(
                _qualification_expected_isolation_observation(baseline),
                post_observation,
            )
        )
    if isolation["observation_error"] is not None:
        expected_isolation_mismatches.append("observation_error")
    if isolation["communication_restored"] is False:
        expected_isolation_mismatches.append("communication_restore")
    if isolation["child_alive"] is not False:
        expected_isolation_mismatches.append("child_process")
    if isolation["mismatches"] != sorted(set(expected_isolation_mismatches)):
        raise OutcomeEvidenceRunnerError(
            "qualification result isolation mismatch labels differ"
        )
    if record["status"] == "passed" and post_observation != (
        _qualification_expected_isolation_observation(baseline)
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification passed result has isolation drift"
        )
    review_binding = _validate_qualification_review_binding(
        record["review_binding"]
    )
    if (
        review_binding["source_commit"] != request["source_commit"]
        or review_binding["request_source"]["path"]
        != request["request_source_path"]
        or review_binding["request_source"]["request_hash"]
        != request["request_hash"]
        or review_binding["active_request"]["path"]
        != request["request_path"]
        or review_binding["allowed_review_paths"]
        != request["review_allowed_paths"]
        or review_binding["registration"] != request["registration"]
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification result review binding mismatch"
        )

    request_created = _timestamp(request.get("created_unix_ns"))
    result_started = _timestamp(record["created_unix_ns"])
    result_ended = _timestamp(record["ended_unix_ns"])
    ordered = request_created <= result_started
    previous = result_started
    loaders = {
        "attempt": load_attempt_record,
        "ready": load_ready_record,
        "release": load_release_record,
    }
    for name in ("attempt", "ready", "release"):
        binding = record["handshake"][name]
        if binding["sha256"] is None:
            continue
        path = _qualification_require_no_follow_path(
            binding["path"],
            f"{name} artifact",
            expected_kind="file",
        )
        if _path_sha256(path, f"qualification {name}") != binding["sha256"]:
            raise OutcomeEvidenceRunnerError(
                f"qualification {name} result hash mismatch"
            )
        handshake_record = loaders[name](path)
        created = _timestamp(handshake_record.get("created_unix_ns"))
        if name == "attempt":
            ordered = ordered and result_started == created
        else:
            ordered = ordered and previous <= created
        previous = created
    ordered = ordered and previous <= result_ended
    if not ordered:
        raise OutcomeEvidenceRunnerError(
            "qualification lifecycle timestamp order is invalid"
        )


def _validate_qualification_runtime_boundaries(
    *,
    request: Mapping[str, Any],
    registration: OutcomeEvidenceRegistration,
    attempt: Mapping[str, Any],
    review_binding: Mapping[str, Any],
    release_allowed: bool,
    release_validation_deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> None:
    def require_release_budget() -> None:
        if release_allowed:
            return
        if release_validation_deadline is None:
            raise OutcomeEvidenceRunnerError(
                "qualification pre-release validation has no deadline"
            )
        _require_qualification_release_validation_budget(
            release_validation_deadline,
            monotonic,
        )

    require_release_budget()
    handshake = request["handshake"]
    attempt_path = _qualification_require_no_follow_path(
        handshake["attempt_path"],
        "attempt artifact",
        expected_kind="file",
    )
    if load_attempt_record(attempt_path) != dict(attempt):
        raise OutcomeEvidenceRunnerError("qualification attempt changed")
    require_release_budget()
    if not release_allowed and _qualification_path_entry_exists(
        Path(handshake["release_path"])
    ):
        raise OutcomeEvidenceRunnerError(
            "qualification release exists before parent publication"
        )
    if release_allowed:
        observed_review_binding = _validate_qualification_review_chain(
            request=request,
            request_source_path=Path(request["request_source_path"]),
            expected_request_bytes=(
                _canonical_json(request) + "\n"
            ).encode("utf-8"),
            expected_review_commit=review_binding["review_commit"],
            expected_request_file_sha256=review_binding["request_source"][
                "file_sha256"
            ],
            expected_request_size=review_binding["request_source"]["size"],
            registration=registration,
            registration_path=Path(request["registration"]["path"]),
            implementation_sha256=request["implementation_sha256"],
        )
        if observed_review_binding != dict(review_binding):
            raise OutcomeEvidenceRunnerError(
                "qualification review binding changed during launch"
            )
    else:
        _validate_qualification_live_review_boundaries(
            request=request,
            registration=registration,
            review_binding=review_binding,
            deadline=release_validation_deadline,
            monotonic=monotonic,
        )
        require_release_budget()
    registration_path = _qualification_require_no_follow_path(
        request["registration"]["path"],
        "registration",
        expected_kind="file",
    )
    if request["registration"]["file_sha256"] != _path_sha256(
        registration_path,
        "qualification registration",
        deadline=None if release_allowed else release_validation_deadline,
        monotonic=monotonic,
    ):
        raise OutcomeEvidenceRunnerError("qualification registration changed")
    require_release_budget()
    config_path = _qualification_require_no_follow_path(
        request["config"]["path"],
        "config",
        expected_kind="file",
    )
    if request["config"]["sha256"] != _path_sha256(
        config_path,
        "qualification config",
        deadline=None if release_allowed else release_validation_deadline,
        monotonic=monotonic,
    ):
        raise OutcomeEvidenceRunnerError("qualification config changed")
    require_release_budget()
    marker_path = _qualification_require_no_follow_path(
        request["marker"]["path"],
        "marker",
        expected_kind="file",
        allow_missing=True,
    )
    if _ai_marker_count(marker_path) != request["marker"][
        "start_count"
    ]:
        raise OutcomeEvidenceRunnerError("qualification marker count changed")
    require_release_budget()
    control_paths = {
        Path(request["request_path"]),
        Path(handshake["attempt_path"]),
        Path(handshake["ready_path"]),
        Path(handshake["release_path"]),
        Path(request["completion_path"]),
        Path(request["failure_path"]),
    }
    _require_paths_absent(
        (
            Path(request["completion_path"]),
            Path(request["failure_path"]),
        ),
        "qualification terminal artifact exists before publication",
    )
    require_release_budget()
    forbidden_paths = {Path(path) for path in request["forbidden_paths"]}
    _require_paths_absent(
        tuple(forbidden_paths),
        "forbidden qualification output exists",
    )
    require_release_budget()
    inventory = _qualification_root_inventory(
        Path(request["qualification_root"]),
        excluded_paths={*control_paths, *forbidden_paths},
        deadline=None if release_allowed else release_validation_deadline,
        monotonic=monotonic,
    )
    if inventory != request["preexisting_files"]:
        raise OutcomeEvidenceRunnerError(
            "qualification preexisting file inventory changed"
        )
    require_release_budget()
    expected_request_bytes = (_canonical_json(request) + "\n").encode("utf-8")
    active_request_path = _qualification_require_no_follow_path(
        request["request_path"],
        "active request",
        expected_kind="file",
    )
    try:
        observed_request_bytes = active_request_path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot reread qualification request: {exc}"
        ) from exc
    if observed_request_bytes != expected_request_bytes:
        raise OutcomeEvidenceRunnerError("qualification request changed")
    require_release_budget()


def _optional_path_sha256(path: Path) -> str | None:
    if not _qualification_path_entry_exists(path):
        return None
    try:
        regular_path = _qualification_require_no_follow_path(
            path,
            "handshake artifact",
            expected_kind="file",
        )
        return hashlib.sha256(regular_path.read_bytes()).hexdigest()
    except (OSError, OutcomeEvidenceRunnerError):
        return None


def _safe_marker_count(path: Path) -> int | None:
    try:
        marker_path = _qualification_require_no_follow_path(
            path,
            "marker",
            expected_kind="file",
            allow_missing=True,
        )
        return _ai_marker_count(marker_path)
    except BaseException:
        return None


def _safe_process_exit_code(process: Any) -> int | None:
    if process is None:
        return None
    try:
        value = process.poll()
    except BaseException:
        return None
    return value if type(value) is int else None


def _child_cleanup_required(process: Any) -> bool:
    if process is None:
        return False
    try:
        return process.poll() is None
    except BaseException:
        return True


def build_slot_launch(
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
    slot_number: int,
) -> RegisteredSlotLaunch:
    """Build one registered launch without touching the filesystem or a process."""

    slot = _registered_slot(registration, slot_number)
    binding = _validate_run_lock_binding(registration, run_lock)
    command = tuple(_registered_command(registration))
    validate_registered_command(registration, command)
    config_record = {
        "category_rates_bps": {"card_reward": 300, "shop": 1000},
        "enabled_categories": ["card_reward", "shop"],
        "manifest_path": slot.manifest_path,
        "per_run_alternative_budget": 2,
        "schema_version": CONFIG_SCHEMA_VERSION,
        "seed": slot.seed,
        "session_id": slot.session_id,
        "source_commit": binding["source_commit"],
        "study_id": registration.study_id,
        "study_registration_hash": registration.registration_hash,
        "study_run_lock_hash": binding["run_lock_hash"],
        "study_slot_number": slot.slot_number,
        "trace_path": slot.trace_path,
    }
    parse_exploration_config(config_record, config_path=Path(slot.config_path))
    return RegisteredSlotLaunch(
        slot_number=slot.slot_number,
        session_id=slot.session_id,
        config_path=slot.config_path,
        command=command,
        environment={CONFIG_ENV: slot.config_path},
        config_record=config_record,
    )


def validate_registered_command(
    registration: OutcomeEvidenceRegistration,
    command: Sequence[str],
) -> tuple[str, ...]:
    if isinstance(command, (str, bytes)) or not isinstance(command, Sequence):
        raise OutcomeEvidenceRunnerError("command must be a sequence of strings")
    normalized = tuple(command)
    if not normalized or any(
        not isinstance(part, str) or not part for part in normalized
    ):
        raise OutcomeEvidenceRunnerError("command contains an invalid argument")
    expected = tuple(_registered_command(registration))
    if normalized != expected:
        raise OutcomeEvidenceRunnerError("command differs from the registered command")
    forbidden = {
        "--train",
        "--model",
        "--epsilon",
        "--expert-mix",
        "--expert-mix-prob",
        "--expert-mix-warmup",
    }
    if forbidden.intersection(normalized) or "--eval" not in normalized:
        raise OutcomeEvidenceRunnerError(
            "command contains a training or policy-mutation flag"
        )
    return normalized


def render_slot_config(launch: RegisteredSlotLaunch) -> str:
    return _canonical_json(dict(launch.config_record)) + "\n"


def write_slot_config_once(launch: RegisteredSlotLaunch) -> str:
    rendered = render_slot_config(launch)
    _publish_text_once(Path(launch.config_path), rendered, "slot config")
    return rendered


def validate_run_lock_or_stop(
    ledger: "StudyLedger",
    *,
    validator: Callable[[], Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Convert any pre-launch lock failure into an irreversible global stop."""

    try:
        run_lock = validator()
        if not isinstance(run_lock, Mapping):
            raise OutcomeEvidenceRunnerError(
                "run lock validator did not return an object"
            )
        observed_hash = _required_sha256(
            run_lock.get("run_lock_hash"), "run lock hash"
        )
        if observed_hash != ledger.run_lock_hash:
            raise OutcomeEvidenceRunnerError(
                "validated run lock differs from the ledger binding"
            )
        return run_lock
    except Exception as exc:
        reason = f"run lock validation failed: {type(exc).__name__}: {exc}"
        if ledger.snapshot()["global_stop"] is None:
            ledger.global_stop(reason=reason)
        raise OutcomeEvidenceRunnerError(reason) from exc


def execute_registered_slot(
    *,
    ledger: "StudyLedger",
    launch: RegisteredSlotLaunch,
    marker_path: Path | str,
    process_runner: Callable[[RegisteredSlotLaunch], int],
    started_unix_ns: int | None = None,
    ended_unix_ns: int | None = None,
) -> dict[str, Any]:
    """Launch one slot and derive completion only from AI marker growth."""

    expected = ledger.next_slot()
    if (
        launch.slot_number != expected.slot_number
        or launch.session_id != expected.session_id
    ):
        raise OutcomeEvidenceRunnerError(
            "launch does not match the next registered ledger slot"
        )
    marker_file = Path(marker_path).resolve()
    before_count = _ai_marker_count(marker_file)
    ledger.start_slot(
        launch.slot_number,
        launch.session_id,
        started_unix_ns=started_unix_ns,
    )
    try:
        exit_code = process_runner(launch)
    except BaseException as exc:
        complete, after_count = _safe_marker_delta_or_stop(
            ledger=ledger,
            marker_path=marker_file,
            before_count=before_count,
            ended_unix_ns=ended_unix_ns,
        )
        if ledger.snapshot()["active_slot"] is not None:
            ledger.recover_active_slot(
                reason=f"child process raised: {type(exc).__name__}",
                complete_trajectories=complete,
                marker_start_count=before_count,
                marker_end_count=after_count,
                ended_unix_ns=ended_unix_ns,
            )
        raise
    complete, after_count = _safe_marker_delta_or_stop(
        ledger=ledger,
        marker_path=marker_file,
        before_count=before_count,
        ended_unix_ns=ended_unix_ns,
    )
    if type(exit_code) is not int:
        ledger.recover_active_slot(
            reason="child process returned a non-integer exit code",
            complete_trajectories=complete,
            marker_start_count=before_count,
            marker_end_count=after_count,
            ended_unix_ns=ended_unix_ns,
        )
        ledger.global_stop(reason="child process exit code was invalid")
        raise OutcomeEvidenceRunnerError("child process exit code is invalid")
    return ledger.finish_slot(
        launch.slot_number,
        process_exit_code=exit_code,
        complete_trajectories=complete,
        marker_start_count=before_count,
        marker_end_count=after_count,
        ended_unix_ns=ended_unix_ns,
    )


def execute_handshaken_registered_slot(
    *,
    ledger: "StudyLedger",
    launch: RegisteredSlotLaunch,
    marker_path: Path | str,
    process_starter: Callable[[RegisteredSlotLaunch, Mapping[str, str]], Any],
    preclaim_validator: Callable[[], Mapping[str, Any]] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    time_ns: Callable[[], int] = time.time_ns,
) -> dict[str, Any]:
    """Claim a registered slot only after its real child proves readiness."""

    expected = ledger.next_slot()
    if (
        launch.slot_number != expected.slot_number
        or launch.session_id != expected.session_id
    ):
        raise OutcomeEvidenceRunnerError(
            "launch does not match the next registered ledger slot"
        )
    if not callable(process_starter):
        raise OutcomeEvidenceRunnerError("process_starter must be callable")
    marker_file = Path(marker_path).resolve()
    rules = registration_handshake_rules(ledger.registration)
    if rules is None:
        raise OutcomeEvidenceRunnerError(
            "launchable registration has no handshake rules"
        )
    paths = _handshake_paths_from_rules(
        config_path=launch.config_path,
        session_id=launch.session_id,
        rules=rules,
    )
    slot = _registered_slot(ledger.registration, launch.slot_number)
    output_paths = (Path(slot.manifest_path), Path(slot.trace_path))
    process = None
    marker_start_count: int | None = None
    try:
        _require_paths_absent(
            (paths.attempt, paths.ready, paths.release),
            "handshake artifact exists before launch",
        )
        _require_paths_absent(
            output_paths,
            "gameplay output exists before launch",
        )
        marker_start_count = _ai_marker_count(marker_file)
        config_path = Path(launch.config_path).resolve()
        config_sha256 = _handshake_file_sha256(
            config_path,
            "registered slot config",
        )
        attempt = build_attempt_record(
            study_id=ledger.registration.study_id,
            registration_hash=ledger.registration.registration_hash,
            run_lock_hash=ledger.run_lock_hash,
            slot_number=launch.slot_number,
            session_id=launch.session_id,
            config_path=config_path,
            config_sha256=config_sha256,
            marker_start_count=marker_start_count,
            paths=paths,
            readiness_timeout_seconds=rules["readiness_timeout_seconds"],
            release_timeout_seconds=rules["release_timeout_seconds"],
            created_unix_ns=_positive_time_ns(time_ns),
        )
        publish_record_once(paths.attempt, attempt)
        child_environment = dict(launch.environment)
        child_environment[HANDSHAKE_ATTEMPT_ENV] = str(paths.attempt)
        process = process_starter(
            launch,
            MappingProxyType(child_environment),
        )
        child_pid = _child_process_pid(process)
        ready = _wait_for_child_readiness(
            process=process,
            child_pid=child_pid,
            attempt=attempt,
            ready_path=paths.ready,
            timeout_seconds=rules["readiness_timeout_seconds"],
            monotonic=monotonic,
            sleep=sleep,
        )
        _validate_preclaim_handshake_state(
            attempt=attempt,
            paths=paths,
            output_paths=output_paths,
            marker_path=marker_file,
            marker_start_count=marker_start_count,
            config_path=config_path,
            config_sha256=config_sha256,
        )
        _validate_preclaim_run_lock(
            preclaim_validator,
            expected_run_lock_hash=ledger.run_lock_hash,
        )
        _require_child_running(process, stage="slot claim")
        ledger.start_slot(
            launch.slot_number,
            launch.session_id,
            marker_start_count=marker_start_count,
            started_unix_ns=_positive_time_ns(time_ns),
        )
        _require_child_running(process, stage="postclaim validation")
        _validate_preclaim_handshake_state(
            attempt=attempt,
            paths=paths,
            output_paths=output_paths,
            marker_path=marker_file,
            marker_start_count=marker_start_count,
            config_path=config_path,
            config_sha256=config_sha256,
            boundary="child release",
        )
        _require_child_running(process, stage="child release")
        release = build_release_record(
            attempt,
            ready,
            created_unix_ns=_positive_time_ns(time_ns),
        )
        publish_record_once(paths.release, release)
    except BaseException as exc:
        active = _ledger_has_active_slot(ledger)
        stage = "postclaim release failed" if active else "preclaim handshake failed"
        reason = f"{stage}: {type(exc).__name__}: {exc}"
        cleanup_error = _terminate_child_process(process)
        if cleanup_error is not None:
            reason = f"{reason}; child cleanup failed: {cleanup_error}"
        if active:
            _recover_claimed_slot_for_stop(
                ledger=ledger,
                marker_path=marker_file,
                marker_start_count=marker_start_count,
                reason=reason,
                ended_unix_ns=_safe_time_ns(time_ns),
            )
        _record_global_stop_once(ledger, reason)
        raise OutcomeEvidenceRunnerError(reason) from exc

    try:
        exit_code = process.wait()
    except BaseException as exc:
        reason = f"released child wait failed: {type(exc).__name__}: {exc}"
        cleanup_error = _terminate_child_process(process)
        if cleanup_error is not None:
            reason = f"{reason}; child cleanup failed: {cleanup_error}"
        _recover_claimed_slot_for_stop(
            ledger=ledger,
            marker_path=marker_file,
            marker_start_count=marker_start_count,
            reason=reason,
            ended_unix_ns=_safe_time_ns(time_ns),
        )
        _record_global_stop_once(ledger, reason)
        raise OutcomeEvidenceRunnerError(reason) from exc
    complete, marker_end_count = _safe_marker_delta_or_stop(
        ledger=ledger,
        marker_path=marker_file,
        before_count=marker_start_count,
        ended_unix_ns=_safe_time_ns(time_ns),
    )
    if type(exit_code) is not int:
        reason = "released child process returned a non-integer exit code"
        ledger.recover_active_slot(
            reason=reason,
            complete_trajectories=complete,
            marker_start_count=marker_start_count,
            marker_end_count=marker_end_count,
            ended_unix_ns=_safe_time_ns(time_ns),
        )
        _record_global_stop_once(ledger, reason)
        raise OutcomeEvidenceRunnerError(reason)
    return ledger.finish_slot(
        launch.slot_number,
        process_exit_code=exit_code,
        complete_trajectories=complete,
        marker_start_count=marker_start_count,
        marker_end_count=marker_end_count,
        ended_unix_ns=_safe_time_ns(time_ns),
    )


def _handshake_paths_from_rules(
    *,
    config_path: Path | str,
    session_id: str,
    rules: Mapping[str, Any],
) -> HandshakePaths:
    parent = Path(config_path).resolve().parent
    return HandshakePaths(
        attempt=(parent / f"{session_id}{rules['attempt_suffix']}").resolve(),
        ready=(parent / f"{session_id}{rules['ready_suffix']}").resolve(),
        release=(parent / f"{session_id}{rules['release_suffix']}").resolve(),
    )


def _wait_for_child_readiness(
    *,
    process: Any,
    child_pid: int,
    attempt: Mapping[str, Any],
    ready_path: Path,
    ready_path_validator: Callable[[Path], Path] | None = None,
    timeout_seconds: int,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    deadline = monotonic() + timeout_seconds
    while True:
        if monotonic() >= deadline:
            raise OutcomeEvidenceRunnerError("child readiness deadline exceeded")
        if _qualification_path_entry_exists(ready_path):
            if monotonic() >= deadline:
                raise OutcomeEvidenceRunnerError("child readiness deadline exceeded")
            if process.poll() is not None:
                raise OutcomeEvidenceRunnerError(
                    "child exited before readiness verification"
                )
            guarded_ready_path = (
                ready_path_validator(ready_path)
                if ready_path_validator is not None
                else ready_path
            )
            ready = load_ready_record(guarded_ready_path)
            validated = validate_ready_record(
                ready,
                attempt=attempt,
                child_pid=child_pid,
            )
            if process.poll() is not None:
                raise OutcomeEvidenceRunnerError(
                    "child exited before readiness verification"
                )
            return validated
        exit_code = process.poll()
        if exit_code is not None:
            raise OutcomeEvidenceRunnerError(
                f"child exited before readiness with code {exit_code}"
            )
        sleep(POLL_INTERVAL_SECONDS)


def _validate_preclaim_handshake_state(
    *,
    attempt: Mapping[str, Any],
    paths: HandshakePaths,
    output_paths: Sequence[Path],
    marker_path: Path,
    marker_start_count: int,
    config_path: Path,
    config_sha256: str,
    boundary: str = "slot claim",
) -> None:
    if load_attempt_record(paths.attempt) != dict(attempt):
        raise OutcomeEvidenceRunnerError(
            f"handshake attempt changed before {boundary}"
        )
    if _qualification_path_entry_exists(paths.release):
        raise OutcomeEvidenceRunnerError(f"release exists before {boundary}")
    _require_paths_absent(
        output_paths,
        f"gameplay output was created before {boundary}",
    )
    if _ai_marker_count(marker_path) != marker_start_count:
        raise OutcomeEvidenceRunnerError(
            f"AI marker count changed before {boundary}"
        )
    if (
        _handshake_file_sha256(config_path, "registered slot config")
        != config_sha256
    ):
        raise OutcomeEvidenceRunnerError(
            f"registered slot config changed before {boundary}"
        )


def _validate_preclaim_run_lock(
    validator: Callable[[], Mapping[str, Any]] | None,
    *,
    expected_run_lock_hash: str,
) -> None:
    if validator is None:
        return
    if not callable(validator):
        raise OutcomeEvidenceRunnerError("preclaim_validator must be callable")
    observed = validator()
    if not isinstance(observed, Mapping):
        raise OutcomeEvidenceRunnerError(
            "preclaim run lock validator returned a non-object"
        )
    if observed.get("run_lock_hash") != expected_run_lock_hash:
        raise OutcomeEvidenceRunnerError(
            "preclaim run lock differs from the ledger binding"
        )


def _require_child_running(process: Any, *, stage: str) -> None:
    exit_code = process.poll()
    if exit_code is not None:
        raise OutcomeEvidenceRunnerError(
            f"child exited before {stage} with code {exit_code}"
        )


def _recover_active_slot_after_host_failure(
    *,
    ledger: "StudyLedger",
    marker_path: Path | str,
    ended_unix_ns: int | None = None,
) -> None:
    snapshot = ledger.snapshot()
    active = snapshot["active_slot"]
    if active is None:
        return
    reason = "active slot recovery after parent or host failure"
    _recover_claimed_slot_for_stop(
        ledger=ledger,
        marker_path=Path(marker_path).resolve(),
        marker_start_count=active.get("marker_start_count"),
        reason=reason,
        ended_unix_ns=ended_unix_ns,
    )
    _record_global_stop_once(ledger, reason)
    raise OutcomeEvidenceRunnerError(reason)


def _recover_claimed_slot_for_stop(
    *,
    ledger: "StudyLedger",
    marker_path: Path,
    marker_start_count: Any,
    reason: str,
    ended_unix_ns: int | None,
) -> None:
    marker_end_count = None
    complete = 0
    recovery_reason = reason
    if type(marker_start_count) is int and marker_start_count >= 0:
        try:
            observed_end = _ai_marker_count(marker_path)
            observed_complete = observed_end - marker_start_count
            if observed_complete < 0 or observed_complete > 25:
                raise OutcomeEvidenceRunnerError(
                    "AI marker delta is outside the registered slot"
                )
            marker_end_count = observed_end
            complete = observed_complete
        except OutcomeEvidenceRunnerError as exc:
            recovery_reason = f"{reason}; marker recovery failed: {exc}"
            marker_start_count = None
            marker_end_count = None
            complete = 0
    else:
        marker_start_count = None
        recovery_reason = f"{reason}; marker start boundary is unavailable"
    ledger.recover_active_slot(
        reason=recovery_reason,
        complete_trajectories=complete,
        marker_start_count=marker_start_count,
        marker_end_count=marker_end_count,
        ended_unix_ns=ended_unix_ns,
    )


def _terminate_child_process(process: Any) -> str | None:
    if process is None:
        return None
    failures = []
    try:
        if process.poll() is not None:
            return None
    except BaseException as exc:
        failures.append(f"poll failed: {type(exc).__name__}: {exc}")
    try:
        process.terminate()
        try:
            process.wait(timeout=_PROCESS_TERMINATION_TIMEOUT_SECONDS)
            return None
        except subprocess.TimeoutExpired:
            failures.append("terminate deadline exceeded")
        except BaseException as exc:
            failures.append(f"terminate wait failed: {type(exc).__name__}: {exc}")
    except BaseException as exc:
        failures.append(f"terminate failed: {type(exc).__name__}: {exc}")
    try:
        process.kill()
        process.wait(timeout=_PROCESS_TERMINATION_TIMEOUT_SECONDS)
        return None
    except BaseException as exc:
        failures.append(f"kill failed: {type(exc).__name__}: {exc}")
    try:
        if process.poll() is not None:
            return None
    except BaseException as exc:
        failures.append(f"final poll failed: {type(exc).__name__}: {exc}")
    return "; ".join(failures) or "child process remains live"


def _ledger_has_active_slot(ledger: "StudyLedger") -> bool:
    try:
        return ledger.snapshot()["active_slot"] is not None
    except OutcomeEvidenceRunnerError:
        return False


def _record_global_stop_once(ledger: "StudyLedger", reason: str) -> None:
    if ledger.snapshot()["global_stop"] is None:
        ledger.global_stop(reason=reason)


def _child_process_pid(process: Any) -> int:
    pid = getattr(process, "pid", None)
    if type(pid) is not int or pid <= 0:
        raise OutcomeEvidenceRunnerError("child process PID is invalid")
    return pid


def _require_paths_absent(paths: Sequence[Path], message: str) -> None:
    existing = [
        str(path) for path in paths if _qualification_path_entry_exists(path)
    ]
    if existing:
        raise OutcomeEvidenceRunnerError(f"{message}: {existing[0]}")


def _qualification_path_entry_exists(path: Path) -> bool:
    try:
        Path(path).lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot inspect qualification path entry {path}: {exc}"
        ) from exc
    return True


def _handshake_file_sha256(path: Path, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(f"cannot read {label}: {exc}") from exc


def _positive_time_ns(clock: Callable[[], int]) -> int:
    value = clock()
    if type(value) is not int or value <= 0:
        raise OutcomeEvidenceRunnerError("clock returned an invalid timestamp")
    return value


def _safe_time_ns(clock: Callable[[], int]) -> int | None:
    try:
        return _positive_time_ns(clock)
    except BaseException:
        return None


def _safe_marker_delta_or_stop(
    *,
    ledger: "StudyLedger",
    marker_path: Path,
    before_count: int,
    ended_unix_ns: int | None,
) -> tuple[int, int]:
    try:
        after_count = _ai_marker_count(marker_path)
        complete = after_count - before_count
        if complete < 0:
            raise OutcomeEvidenceRunnerError("AI marker file was truncated")
        if complete > 25:
            raise OutcomeEvidenceRunnerError(
                "AI marker delta exceeds the registered 25-game slot"
            )
        return complete, after_count
    except OutcomeEvidenceRunnerError as exc:
        if ledger.snapshot()["active_slot"] is not None:
            ledger.recover_active_slot(
                reason=f"marker integrity failure: {exc}",
                complete_trajectories=0,
                ended_unix_ns=ended_unix_ns,
            )
        ledger.global_stop(reason=f"marker integrity failure: {exc}")
        raise


def _ai_marker_count(path: Path) -> int:
    return len(_load_ai_markers(path))


def _load_ai_markers(path: Path) -> list[int]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise OutcomeEvidenceRunnerError(f"cannot read AI marker file: {exc}") from exc
    raw_markers = [line.strip() for line in lines if line.strip()]
    if any(not marker.isdigit() for marker in raw_markers):
        raise OutcomeEvidenceRunnerError("AI marker file contains an invalid marker")
    return [int(marker) for marker in raw_markers]


def conservative_run_join_count(
    *,
    marker_timestamps: Sequence[int],
    run_timestamps: Sequence[int],
    tolerance_seconds: int = 10,
) -> int:
    """Count only markers with one unique, unused nearby run filename."""
    try:
        return len(
            conservative_marker_run_pairs(
                marker_timestamps=marker_timestamps,
                run_timestamps=run_timestamps,
                tolerance_seconds=tolerance_seconds,
            )
        )
    except ValueError as exc:
        raise OutcomeEvidenceRunnerError(str(exc)) from exc


def build_blinded_monitor(
    *,
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
    ledger_snapshot: Mapping[str, Any],
    structural_observations: Sequence[Mapping[str, Any]],
    run_lock_valid: bool = True,
) -> dict[str, Any]:
    """Build an allowlisted collection monitor with no outcome surface."""

    binding = _validate_run_lock_binding(registration, run_lock)
    handshake_rules = registration_handshake_rules(registration)
    if isinstance(structural_observations, (str, bytes)) or not isinstance(
        structural_observations, Sequence
    ):
        raise OutcomeEvidenceRunnerError(
            "structural observations must be a sequence"
        )
    if not isinstance(ledger_snapshot, Mapping):
        raise OutcomeEvidenceRunnerError("ledger snapshot must be an object")
    if type(run_lock_valid) is not bool:
        raise OutcomeEvidenceRunnerError("run_lock_valid must be a boolean")

    blockers: set[str] = set()
    if not run_lock_valid:
        blockers.add("run_lock_invalid")
    observations_by_slot: dict[int, Mapping[str, Any]] = {}
    registered_sessions = {
        slot.slot_number: slot.session_id for slot in registration.slots
    }
    for observation in structural_observations:
        if not isinstance(observation, Mapping):
            blockers.add("invalid_structural_observation")
            continue
        slot_number = observation.get("slot_number")
        session_id = observation.get("session_id")
        if (
            type(slot_number) is not int
            or registered_sessions.get(slot_number) != session_id
        ):
            blockers.add("unregistered_structural_observation")
            continue
        if slot_number in observations_by_slot:
            blockers.add(f"duplicate_structural_observation_slot_{slot_number:02d}")
            continue
        observations_by_slot[slot_number] = observation

    active = ledger_snapshot.get("active_slot")
    active_number = active.get("slot_number") if isinstance(active, Mapping) else None
    terminal_records = ledger_snapshot.get("terminal_slots")
    if not isinstance(terminal_records, Sequence):
        raise OutcomeEvidenceRunnerError("ledger terminal_slots is invalid")
    terminal_by_slot = {
        record.get("slot_number"): record
        for record in terminal_records
        if isinstance(record, Mapping)
    }
    launched_numbers = set(terminal_by_slot)
    if type(active_number) is int:
        launched_numbers.add(active_number)

    slots = []
    for slot in registration.slots:
        if slot.slot_number in terminal_by_slot:
            lifecycle = str(
                terminal_by_slot[slot.slot_number].get("terminal_status")
            )
            process_exit_code = terminal_by_slot[slot.slot_number].get(
                "process_exit_code"
            )
        elif slot.slot_number == active_number:
            lifecycle = "active"
            process_exit_code = None
        else:
            lifecycle = "unlaunched"
            process_exit_code = None
        observation = observations_by_slot.get(slot.slot_number)
        if slot.slot_number in launched_numbers and observation is None:
            blockers.add(f"missing_launched_slot_{slot.slot_number:02d}")
        structural = _sanitize_structural_observation(
            observation,
            slot_number=slot.slot_number,
            blockers=blockers,
        )
        handshake_paths = (
            None
            if handshake_rules is None
            else _handshake_paths_from_rules(
                config_path=slot.config_path,
                session_id=slot.session_id,
                rules=handshake_rules,
            )
        )
        structural.update(
            {
                "handshake_attempt_path": (
                    str(handshake_paths.attempt)
                    if handshake_paths is not None
                    else None
                ),
                "handshake_ready_path": (
                    str(handshake_paths.ready)
                    if handshake_paths is not None
                    else None
                ),
                "handshake_release_path": (
                    str(handshake_paths.release)
                    if handshake_paths is not None
                    else None
                ),
            }
        )
        handshake_status = structural["handshake_status"]
        if handshake_rules is not None and handshake_status == "invalid":
            blockers.add(f"invalid_handshake_sequence_slot_{slot.slot_number:02d}")
        if handshake_rules is not None and lifecycle in {
            "active",
            "completed",
            "interrupted",
        } and (
            handshake_status != "released"
        ):
            blockers.add(f"launched_slot_handshake_missing_{slot.slot_number:02d}")
        if (
            handshake_rules is not None
            and lifecycle == "unlaunched"
            and handshake_status != "not_started"
        ):
            blockers.add(f"unlaunched_slot_handshake_{slot.slot_number:02d}")
        if lifecycle == "active" and not structural["config_exists"]:
            blockers.add(f"active_slot_config_missing_{slot.slot_number:02d}")
        if lifecycle in {"completed", "interrupted"} and (
            not structural["config_exists"]
            or not structural["manifest_exists"]
            or not structural["trace_exists"]
            or not structural["isolation_verified"]
        ):
            blockers.add(f"terminal_slot_structure_invalid_{slot.slot_number:02d}")
        slots.append(
            {
                **structural,
                "lifecycle": lifecycle,
                "process_exit_code": process_exit_code,
                "session_id": slot.session_id,
                "slot_number": slot.slot_number,
            }
        )

    global_stop = ledger_snapshot.get("global_stop") is not None
    if global_stop:
        blockers.add("global_integrity_stop_recorded")
    all_terminal = ledger_snapshot.get("all_slots_terminal") is True
    phase = "blocked" if global_stop else "terminal" if all_terminal else "collection"
    return {
        "blockers": sorted(blockers),
        "global_integrity_stop": global_stop,
        "integrity_valid": not blockers,
        "launched_slot_count": len(launched_numbers),
        "phase": phase,
        "registration_valid": True,
        "registration_hash": registration.registration_hash,
        "run_lock_valid": run_lock_valid,
        "run_lock_hash": binding["run_lock_hash"],
        "schema_version": MONITOR_SCHEMA_VERSION,
        "slot_count": len(registration.slots),
        "slots": slots,
        "study_id": registration.study_id,
        "terminal_slot_count": len(terminal_by_slot),
    }


def _sanitize_structural_observation(
    observation: Mapping[str, Any] | None,
    *,
    slot_number: int,
    blockers: set[str],
) -> dict[str, Any]:
    defaults = {
        "candidate_legal_records": 0,
        "config_exists": False,
        "config_sha256": None,
        "confirmed_records": 0,
        "handshake_attempt_exists": False,
        "handshake_attempt_sha256": None,
        "handshake_ready_exists": False,
        "handshake_ready_sha256": None,
        "handshake_release_exists": False,
        "handshake_release_sha256": None,
        "handshake_status": "not_started",
        "isolation_verified": False,
        "manifest_exists": False,
        "manifest_hash": None,
        "manifest_sha256": None,
        "proposed_records": 0,
        "replay_valid_records": 0,
        "run_join_complete_count": 0,
        "trace_exists": False,
        "trace_sha256": None,
    }
    if observation is None:
        return defaults
    valid = observation.get("structural_valid", True) is True
    boolean_fields = (
        "config_exists",
        "handshake_attempt_exists",
        "handshake_ready_exists",
        "handshake_release_exists",
        "isolation_verified",
        "manifest_exists",
        "trace_exists",
    )
    count_fields = (
        "candidate_legal_records",
        "confirmed_records",
        "proposed_records",
        "replay_valid_records",
        "run_join_complete_count",
    )
    hash_fields = (
        "config_sha256",
        "handshake_attempt_sha256",
        "handshake_ready_sha256",
        "handshake_release_sha256",
        "manifest_hash",
        "manifest_sha256",
        "trace_sha256",
    )
    result = dict(defaults)
    for field in boolean_fields:
        value = observation.get(field)
        if type(value) is not bool:
            valid = False
        else:
            result[field] = value
    for field in count_fields:
        value = observation.get(field)
        if type(value) is not int or value < 0:
            valid = False
        else:
            result[field] = value
    for field in hash_fields:
        value = observation.get(field)
        if value is not None and (
            not isinstance(value, str) or not _is_lower_hex(value, _SHA256_LENGTH)
        ):
            valid = False
        else:
            result[field] = value
    if (
        result["confirmed_records"] > result["proposed_records"]
        or result["replay_valid_records"] > result["confirmed_records"]
        or result["candidate_legal_records"] > result["replay_valid_records"]
        or (result["config_exists"] and result["config_sha256"] is None)
        or result["handshake_attempt_exists"]
        != (result["handshake_attempt_sha256"] is not None)
        or result["handshake_ready_exists"]
        != (result["handshake_ready_sha256"] is not None)
        or result["handshake_release_exists"]
        != (result["handshake_release_sha256"] is not None)
        or (
            result["manifest_exists"]
            and (
                result["manifest_sha256"] is None
                or result["manifest_hash"] is None
            )
        )
        or (result["trace_exists"] and result["trace_sha256"] is None)
    ):
        valid = False
    if not valid:
        blockers.add(f"invalid_structural_observation_slot_{slot_number:02d}")
        return defaults
    handshake_shape = (
        result["handshake_attempt_exists"],
        result["handshake_ready_exists"],
        result["handshake_release_exists"],
    )
    result["handshake_status"] = {
        (False, False, False): "not_started",
        (True, False, False): "attempted",
        (True, True, False): "ready",
        (True, True, True): "released",
    }.get(handshake_shape, "invalid")
    return result


def render_blinded_monitor_json(monitor: Mapping[str, Any]) -> str:
    return _canonical_json(monitor) + "\n"


def render_blinded_monitor_markdown(monitor: Mapping[str, Any]) -> str:
    integrity = "valid" if monitor.get("integrity_valid") is True else "blocked"
    lines = [
        "# Blinded Structural Monitor",
        "",
        f"- Study: `{monitor.get('study_id')}`",
        f"- Phase: `{monitor.get('phase')}`",
        f"- Integrity: `{integrity}`",
        (
            f"- Progress: {monitor.get('terminal_slot_count')}/"
            f"{monitor.get('slot_count')} terminal slots"
        ),
        "",
        "| Slot | Session | Lifecycle | Handshake | Exit | Config | Manifest | Trace | "
        "Proposed | Confirmed | Replay valid | Candidate legal | "
        "Complete joins | Isolation |",
        "|---:|---|---|---|---:|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    slots = monitor.get("slots", [])
    for slot in slots:
        lines.append(
            "| {slot_number:02d} | `{session_id}` | {lifecycle} | "
            "{handshake_status} | "
            "{process_exit_code} | {config} | "
            "{manifest} | {trace} | {proposed_records} | {confirmed_records} | "
            "{replay_valid_records} | {candidate_legal_records} | "
            "{run_join_complete_count} | {isolation} |".format(
                **slot,
                config="yes" if slot["config_exists"] else "no",
                manifest="yes" if slot["manifest_exists"] else "no",
                trace="yes" if slot["trace_exists"] else "no",
                isolation="valid" if slot["isolation_verified"] else "not-valid",
            )
        )
    blockers = monitor.get("blockers", [])
    if blockers:
        lines.extend(["", "## Structural Blockers", ""])
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    return "\n".join(lines) + "\n"


def collect_structural_observations(
    *,
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
    ledger_snapshot: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Inspect launched artifacts while retaining only structural fields."""

    binding = _validate_run_lock_binding(registration, run_lock)
    handshake_rules = registration_handshake_rules(registration)
    active = ledger_snapshot.get("active_slot")
    active_number = active.get("slot_number") if isinstance(active, Mapping) else None
    terminal_records = ledger_snapshot.get("terminal_slots", [])
    terminal_by_slot = {
        record.get("slot_number"): record
        for record in terminal_records
        if isinstance(record, Mapping)
    }
    launched_numbers = set(terminal_by_slot)
    if type(active_number) is int:
        launched_numbers.add(active_number)
    handshake_paths_by_slot = {}
    observed_numbers = set(launched_numbers)
    for registered_slot in registration.slots:
        registered_paths = (
            None
            if handshake_rules is None
            else _handshake_paths_from_rules(
                config_path=registered_slot.config_path,
                session_id=registered_slot.session_id,
                rules=handshake_rules,
            )
        )
        handshake_paths_by_slot[registered_slot.slot_number] = registered_paths
        if registered_paths is not None and any(
            path.exists()
            for path in (
                registered_paths.attempt,
                registered_paths.ready,
                registered_paths.release,
            )
        ):
            observed_numbers.add(registered_slot.slot_number)

    game_root = Path(registration.checkpoint_root).resolve().parent
    join_inputs_valid = True
    try:
        marker_timestamps = _load_ai_markers(
            game_root / "runs" / "ai_games.txt"
        )
        run_timestamps = []
        for run_path in (game_root / "runs" / "IRONCLAD").glob("*.run"):
            if run_path.stem.isdigit():
                run_timestamps.append(int(run_path.stem))
    except (OSError, OutcomeEvidenceRunnerError):
        marker_timestamps = []
        run_timestamps = []
        join_inputs_valid = False

    observations = []
    for slot_number in sorted(observed_numbers):
        slot = _registered_slot(registration, slot_number)
        handshake_paths = handshake_paths_by_slot[slot_number]
        terminal = terminal_by_slot.get(slot_number, {})
        marker_start = terminal.get("marker_start_count")
        marker_end = terminal.get("marker_end_count")
        run_join_complete_count = 0
        slot_join_valid = join_inputs_valid
        if terminal:
            if (
                type(marker_start) is int
                and type(marker_end) is int
                and 0 <= marker_start <= marker_end <= len(marker_timestamps)
            ):
                run_join_complete_count = conservative_run_join_count(
                    marker_timestamps=marker_timestamps[marker_start:marker_end],
                    run_timestamps=run_timestamps,
                )
            else:
                slot_join_valid = False
        observation = {
            "candidate_legal_records": 0,
            "config_exists": False,
            "config_sha256": None,
            "confirmed_records": 0,
            "handshake_attempt_exists": False,
            "handshake_attempt_sha256": None,
            "handshake_ready_exists": False,
            "handshake_ready_sha256": None,
            "handshake_release_exists": False,
            "handshake_release_sha256": None,
            "isolation_verified": False,
            "manifest_exists": False,
            "manifest_hash": None,
            "manifest_sha256": None,
            "proposed_records": 0,
            "replay_valid_records": 0,
            "run_join_complete_count": run_join_complete_count,
            "session_id": slot.session_id,
            "slot_number": slot.slot_number,
            "structural_valid": slot_join_valid,
            "trace_exists": False,
            "trace_sha256": None,
        }
        config_path = Path(slot.config_path)
        manifest_path = Path(slot.manifest_path)
        trace_path = Path(slot.trace_path)
        try:
            if handshake_paths is not None:
                for name, handshake_path in (
                    ("attempt", handshake_paths.attempt),
                    ("ready", handshake_paths.ready),
                    ("release", handshake_paths.release),
                ):
                    if handshake_path.exists():
                        observation[f"handshake_{name}_exists"] = True
                        if not handshake_path.is_file():
                            raise OutcomeEvidenceRunnerError(
                                f"handshake {name} artifact is not a file"
                            )
                        observation[f"handshake_{name}_sha256"] = _sha256_file(
                            handshake_path
                        )
            if config_path.is_file():
                observation["config_exists"] = True
                observation["config_sha256"] = _sha256_file(config_path)
                config = load_exploration_config(config_path)
                if (
                    config.session_id != slot.session_id
                    or config.study_id != registration.study_id
                    or config.study_slot_number != slot.slot_number
                    or config.study_registration_hash
                    != registration.registration_hash
                    or config.study_run_lock_hash != binding["run_lock_hash"]
                    or config.source_commit != binding["source_commit"]
                ):
                    raise OutcomeEvidenceRunnerError(
                        "registered config binding mismatch"
                    )
            else:
                config = None

            manifest = None
            if manifest_path.is_file():
                observation["manifest_exists"] = True
                observation["manifest_sha256"] = _sha256_file(manifest_path)
                manifest = _load_json_object(manifest_path, "manifest")
                manifest_hash = manifest.get("manifest_hash")
                if not isinstance(manifest_hash, str) or not _is_lower_hex(
                    manifest_hash, _SHA256_LENGTH
                ):
                    raise OutcomeEvidenceRunnerError("manifest hash is invalid")
                observation["manifest_hash"] = manifest_hash
                effective = manifest.get("effective_config")
                if not isinstance(effective, Mapping) or (
                    effective.get("study_run_lock_hash")
                    != binding["run_lock_hash"]
                ):
                    raise OutcomeEvidenceRunnerError(
                        "manifest run lock binding mismatch"
                    )
                observation["isolation_verified"] = (
                    manifest_isolation_matches_run_lock(manifest, run_lock)
                )

            if trace_path.is_file():
                observation["trace_exists"] = True
                observation["trace_sha256"] = _sha256_file(trace_path)

            if config is not None and manifest is not None and trace_path.is_file():
                from analysis_scripts.noncombat_exploration_evidence import (
                    export_confirmed_exploration_samples,
                )

                export = export_confirmed_exploration_samples(
                    trace_path,
                    manifest_path,
                    expected_source_commit=binding["source_commit"],
                )
                summary = export.validation_summary
                observation["proposed_records"] = summary["proposed_records"]
                observation["confirmed_records"] = summary["confirmed"]
                observation["replay_valid_records"] = summary["replay_valid"]
                observation["candidate_legal_records"] = summary[
                    "candidate_legal"
                ]
        except Exception:
            observation["structural_valid"] = False
        observations.append(observation)
    return observations


def write_blinded_monitor_artifacts(
    monitor: Mapping[str, Any],
    *,
    json_path: Path | str,
    markdown_path: Path | str,
) -> dict[str, str]:
    rendered_json = render_blinded_monitor_json(monitor)
    rendered_markdown = render_blinded_monitor_markdown(monitor)
    resolved_json = Path(json_path).resolve()
    resolved_markdown = Path(markdown_path).resolve()
    if resolved_json == resolved_markdown:
        raise OutcomeEvidenceRunnerError("monitor output paths must be distinct")
    _replace_text_atomically(resolved_json, rendered_json)
    _replace_text_atomically(resolved_markdown, rendered_markdown)
    return {
        "json_path": str(resolved_json),
        "markdown_path": str(resolved_markdown),
    }


def _replace_text_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        descriptor, name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(
            f"cannot update monitor artifact {path}: {exc}"
        ) from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(f"cannot hash artifact {path}: {exc}") from exc


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise OutcomeEvidenceRunnerError(f"{label} must be an object")
    return payload


class StudyLedger:
    """Hash-chained append-only lifecycle ledger for one registered schedule."""

    error_type = OutcomeEvidenceRunnerError

    def __init__(
        self,
        *,
        path: Path | str,
        registration: OutcomeEvidenceRegistration,
        run_lock_hash: str,
    ) -> None:
        self.path = Path(path).resolve()
        self.registration = registration
        self.run_lock_hash = _required_sha256(run_lock_hash, "run lock hash")
        self._slots = {slot.slot_number: slot for slot in registration.slots}

    @classmethod
    def open_existing(
        cls,
        *,
        path: Path | str,
        registration: OutcomeEvidenceRegistration,
    ) -> "StudyLedger":
        """Open a ledger using its validated first record as the lock binding."""

        resolved_path = Path(path).resolve()
        try:
            content = resolved_path.read_bytes()
        except OSError as exc:
            raise OutcomeEvidenceRunnerError(
                f"cannot read existing ledger: {exc}"
            ) from exc
        if not content or not content.endswith(b"\n"):
            raise OutcomeEvidenceRunnerError(
                "existing ledger is empty or has a partial final record"
            )
        try:
            first_record = json.loads(
                content.splitlines()[0].decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise OutcomeEvidenceRunnerError(
                f"invalid first ledger record: {exc}"
            ) from exc
        if not isinstance(first_record, Mapping):
            raise OutcomeEvidenceRunnerError(
                "first ledger record must be an object"
            )
        run_lock_hash = _required_sha256(
            first_record.get("run_lock_hash"), "ledger run lock hash"
        )
        _validate_ledger_record(
            first_record,
            sequence=1,
            previous_hash=None,
            registration=registration,
            run_lock_hash=run_lock_hash,
        )
        ledger = cls(
            path=resolved_path,
            registration=registration,
            run_lock_hash=run_lock_hash,
        )
        snapshot = ledger.snapshot()
        if not snapshot["initialized"]:
            raise OutcomeEvidenceRunnerError(
                "existing ledger is not initialized"
            )
        return ledger

    def initialize(self, *, created_unix_ns: int | None = None) -> dict[str, Any]:
        created = _timestamp(created_unix_ns)

        def validate(snapshot: Mapping[str, Any]) -> None:
            if snapshot["initialized"]:
                raise OutcomeEvidenceRunnerError("study ledger is already initialized")

        return self._append(
            event="study_started",
            created_unix_ns=created,
            slot=None,
            payload={"slot_count": len(self.registration.slots)},
            validate=validate,
        )

    def start_slot(
        self,
        slot_number: int,
        session_id: str,
        *,
        marker_start_count: int | None = None,
        started_unix_ns: int | None = None,
    ) -> dict[str, Any]:
        created = _timestamp(started_unix_ns)
        requested_slot = _exact_int(slot_number, "slot_number")
        if marker_start_count is not None and (
            type(marker_start_count) is not int or marker_start_count < 0
        ):
            raise OutcomeEvidenceRunnerError(
                "marker_start_count must be a nonnegative integer"
            )

        def validate(snapshot: Mapping[str, Any]) -> None:
            expected = self._next_slot_from_snapshot(snapshot)
            if requested_slot != expected.slot_number:
                raise OutcomeEvidenceRunnerError(
                    "out of order launch: next registered slot is "
                    f"{expected.slot_number}"
                )
            if session_id != expected.session_id:
                raise OutcomeEvidenceRunnerError(
                    "session_id does not match the next registered slot"
                )

        return self._append(
            event="slot_started",
            created_unix_ns=created,
            slot=self._slots.get(requested_slot),
            payload=(
                {}
                if marker_start_count is None
                else {"marker_start_count": marker_start_count}
            ),
            validate=validate,
        )

    def finish_slot(
        self,
        slot_number: int,
        *,
        process_exit_code: int,
        complete_trajectories: int,
        marker_start_count: int | None = None,
        marker_end_count: int | None = None,
        ended_unix_ns: int | None = None,
    ) -> dict[str, Any]:
        created = _timestamp(ended_unix_ns)
        requested_slot = _exact_int(slot_number, "slot_number")
        exit_code = _exact_int(process_exit_code, "process_exit_code")
        complete = _bounded_count(complete_trajectories)
        marker_start, marker_end = _marker_bounds(
            marker_start_count,
            marker_end_count,
            complete_trajectories=complete,
        )
        terminal_status = (
            "completed" if exit_code == 0 and complete == 25 else "interrupted"
        )

        def validate(snapshot: Mapping[str, Any]) -> None:
            active = snapshot["active_slot"]
            if active is None:
                raise OutcomeEvidenceRunnerError(
                    "no active slot; duplicate terminal transition refused"
                )
            if active["slot_number"] != requested_slot:
                raise OutcomeEvidenceRunnerError("terminal slot is not the active slot")

        slot = self._slots.get(requested_slot)
        record = self._append(
            event="slot_terminal",
            created_unix_ns=created,
            slot=slot,
            payload={
                "complete_trajectories": complete,
                "marker_end_count": marker_end,
                "marker_start_count": marker_start,
                "process_exit_code": exit_code,
                "terminal_status": terminal_status,
            },
            validate=validate,
        )
        return dict(record["payload"])

    def recover_active_slot(
        self,
        *,
        reason: str,
        complete_trajectories: int,
        marker_start_count: int | None = None,
        marker_end_count: int | None = None,
        ended_unix_ns: int | None = None,
    ) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason.strip():
            raise OutcomeEvidenceRunnerError("recovery reason must be nonempty")
        complete = _bounded_count(complete_trajectories)
        marker_start, marker_end = _marker_bounds(
            marker_start_count,
            marker_end_count,
            complete_trajectories=complete,
        )
        created = _timestamp(ended_unix_ns)
        selected_slot: RegisteredSlot | None = None

        def validate(snapshot: Mapping[str, Any]) -> None:
            nonlocal selected_slot
            active = snapshot["active_slot"]
            if active is None:
                raise OutcomeEvidenceRunnerError("there is no active slot to recover")
            selected_slot = self._slots[active["slot_number"]]

        record = self._append(
            event="slot_terminal",
            created_unix_ns=created,
            slot_getter=lambda: selected_slot,
            payload={
                "complete_trajectories": complete,
                "marker_end_count": marker_end,
                "marker_start_count": marker_start,
                "process_exit_code": None,
                "reason": reason.strip(),
                "terminal_status": "interrupted",
            },
            validate=validate,
        )
        return dict(record["payload"])

    def global_stop(
        self, *, reason: str, created_unix_ns: int | None = None
    ) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason.strip():
            raise OutcomeEvidenceRunnerError("global stop reason must be nonempty")
        created = _timestamp(created_unix_ns)

        def validate(snapshot: Mapping[str, Any]) -> None:
            if not snapshot["initialized"]:
                raise OutcomeEvidenceRunnerError("study ledger is not initialized")
            if snapshot["global_stop"] is not None:
                raise OutcomeEvidenceRunnerError("duplicate global stop refused")

        record = self._append(
            event="global_stop",
            created_unix_ns=created,
            slot=None,
            payload={"reason": reason.strip()},
            validate=validate,
        )
        return dict(record["payload"])

    def next_slot(self) -> RegisteredSlot:
        return self._next_slot_from_snapshot(self.snapshot())

    def snapshot(self) -> dict[str, Any]:
        return self._reduce(self._read_records())

    def _next_slot_from_snapshot(
        self, snapshot: Mapping[str, Any]
    ) -> RegisteredSlot:
        if not snapshot["initialized"]:
            raise OutcomeEvidenceRunnerError("study ledger is not initialized")
        if snapshot["global_stop"] is not None:
            raise OutcomeEvidenceRunnerError("global stop prevents later launches")
        if snapshot["active_slot"] is not None:
            raise OutcomeEvidenceRunnerError(
                "active slot must become terminal before the next launch"
            )
        next_number = snapshot["terminal_slot_count"] + 1
        if next_number > len(self.registration.slots):
            raise OutcomeEvidenceRunnerError(
                "registered schedule is complete; there is no later slot"
            )
        return self._slots[next_number]

    def _append(
        self,
        *,
        event: str,
        created_unix_ns: int,
        payload: Mapping[str, Any],
        validate: Callable[[Mapping[str, Any]], None],
        slot: RegisteredSlot | None = None,
        slot_getter: Callable[[], RegisteredSlot | None] | None = None,
    ) -> dict[str, Any]:
        lock_path = self.path.with_name(self.path.name + ".append.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock_descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            raise OutcomeEvidenceRunnerError(
                f"ledger append lock already exists: {lock_path}"
            ) from exc
        try:
            records = self._read_records()
            snapshot = self._reduce(records)
            validate(snapshot)
            if slot_getter is not None:
                slot = slot_getter()
            if event.startswith("slot_") and slot is None:
                raise OutcomeEvidenceRunnerError("slot event has no registered slot")
            previous_hash = records[-1]["record_hash"] if records else None
            record = {
                "created_unix_ns": created_unix_ns,
                "event": event,
                "payload": dict(payload),
                "previous_record_hash": previous_hash,
                "record_hash": None,
                "registration_hash": self.registration.registration_hash,
                "run_lock_hash": self.run_lock_hash,
                "schema_version": LEDGER_SCHEMA_VERSION,
                "sequence": len(records) + 1,
                "session_id": slot.session_id if slot is not None else None,
                "slot_number": slot.slot_number if slot is not None else None,
                "study_id": self.registration.study_id,
            }
            record["record_hash"] = _record_hash(record)
            self._append_line(_canonical_json(record).encode("utf-8") + b"\n")
            return json.loads(_canonical_json(record))
        finally:
            os.close(lock_descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _append_line(self, encoded: bytes) -> None:
        descriptor = os.open(
            self.path,
            os.O_APPEND | os.O_CREAT | os.O_WRONLY,
        )
        try:
            written = os.write(descriptor, encoded)
            if written != len(encoded):
                raise OutcomeEvidenceRunnerError("partial ledger append detected")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            content = self.path.read_bytes()
        except OSError as exc:
            raise OutcomeEvidenceRunnerError(f"cannot read ledger: {exc}") from exc
        if not content:
            return []
        if not content.endswith(b"\n"):
            raise OutcomeEvidenceRunnerError("ledger has a partial final record")
        records = []
        previous_hash = None
        for index, raw_line in enumerate(content.splitlines(), start=1):
            try:
                record = json.loads(
                    raw_line.decode("utf-8"),
                    object_pairs_hook=_reject_duplicate_keys,
                    parse_constant=_reject_json_constant,
                )
            except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
                raise OutcomeEvidenceRunnerError(
                    f"invalid ledger record {index}: {exc}"
                ) from exc
            _validate_ledger_record(
                record,
                sequence=index,
                previous_hash=previous_hash,
                registration=self.registration,
                run_lock_hash=self.run_lock_hash,
            )
            previous_hash = record["record_hash"]
            records.append(record)
        return records

    def _reduce(self, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        initialized = False
        active_slot = None
        terminal_slots = []
        global_stop = None
        for record in records:
            event = record["event"]
            if event == "study_started":
                if initialized or record["sequence"] != 1:
                    raise OutcomeEvidenceRunnerError(
                        "duplicate or misplaced study_started record"
                    )
                initialized = True
            elif event == "slot_started":
                if (
                    not initialized
                    or active_slot is not None
                    or global_stop is not None
                ):
                    raise OutcomeEvidenceRunnerError("invalid slot_started lifecycle")
                expected = len(terminal_slots) + 1
                if record["slot_number"] != expected:
                    raise OutcomeEvidenceRunnerError("ledger slot order mismatch")
                active_slot = {
                    "marker_start_count": record["payload"].get(
                        "marker_start_count"
                    ),
                    "session_id": record["session_id"],
                    "slot_number": record["slot_number"],
                }
            elif event == "slot_terminal":
                if active_slot is None:
                    raise OutcomeEvidenceRunnerError(
                        "terminal record has no active slot"
                    )
                if record["slot_number"] != active_slot["slot_number"]:
                    raise OutcomeEvidenceRunnerError("terminal record slot mismatch")
                if (
                    active_slot["marker_start_count"] is not None
                    and record["payload"].get("marker_start_count")
                    != active_slot["marker_start_count"]
                ):
                    raise OutcomeEvidenceRunnerError(
                        "terminal marker start differs from slot claim"
                    )
                terminal_slots.append(
                    {
                        "complete_trajectories": record["payload"].get(
                            "complete_trajectories"
                        ),
                        "marker_end_count": record["payload"].get(
                            "marker_end_count"
                        ),
                        "marker_start_count": record["payload"].get(
                            "marker_start_count"
                        ),
                        "process_exit_code": record["payload"].get(
                            "process_exit_code"
                        ),
                        "session_id": record["session_id"],
                        "slot_number": record["slot_number"],
                        "terminal_status": record["payload"].get("terminal_status"),
                    }
                )
                active_slot = None
            elif event == "global_stop":
                if not initialized or global_stop is not None:
                    raise OutcomeEvidenceRunnerError("invalid global_stop lifecycle")
                global_stop = {"reason": record["payload"].get("reason")}
            else:
                raise OutcomeEvidenceRunnerError(f"unsupported ledger event: {event}")
        return {
            "active_slot": active_slot,
            "all_slots_terminal": (
                initialized
                and active_slot is None
                and len(terminal_slots) == len(self.registration.slots)
            ),
            "global_stop": global_stop,
            "initialized": initialized,
            "terminal_slot_count": len(terminal_slots),
            "terminal_slots": terminal_slots,
        }


def _registered_slot(
    registration: OutcomeEvidenceRegistration, slot_number: int
) -> RegisteredSlot:
    number = _exact_int(slot_number, "slot_number")
    if number < 1 or number > len(registration.slots):
        raise OutcomeEvidenceRunnerError("slot_number is not registered")
    slot = registration.slots[number - 1]
    if slot.slot_number != number:
        raise OutcomeEvidenceRunnerError("registration slot order is invalid")
    return slot


def _validate_run_lock_binding(
    registration: OutcomeEvidenceRegistration,
    run_lock: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(run_lock, Mapping):
        raise OutcomeEvidenceRunnerError("run lock must be an object")
    run_lock_hash = _required_sha256(run_lock.get("run_lock_hash"), "run lock hash")
    if run_lock.get("study_id") != registration.study_id:
        raise OutcomeEvidenceRunnerError("run lock study_id mismatch")
    registration_binding = run_lock.get("registration")
    if not isinstance(registration_binding, Mapping) or registration_binding.get(
        "canonical_hash"
    ) != registration.registration_hash:
        raise OutcomeEvidenceRunnerError("run lock registration hash mismatch")
    source = run_lock.get("source")
    source_commit = source.get("commit") if isinstance(source, Mapping) else None
    if not isinstance(source_commit, str) or not _is_lower_hex(
        source_commit, _GIT_COMMIT_LENGTH
    ):
        raise OutcomeEvidenceRunnerError("run lock source commit is invalid")
    return {"run_lock_hash": run_lock_hash, "source_commit": source_commit}


def _registered_command(registration: OutcomeEvidenceRegistration) -> list[str]:
    command_record = registration.to_record()["command"]
    return [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]


def _qualification_child_command(
    registration: OutcomeEvidenceRegistration,
) -> list[str]:
    command = _registered_command(registration)
    return [command[0], "-I", "-S", *command[1:]]


def _qualification_child_environment(
    *,
    config_path: str,
    attempt_path: str,
    attempt_hash: str,
) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("PYTHON", "GIT_"))
    }
    environment[CONFIG_ENV] = config_path
    environment[HANDSHAKE_ATTEMPT_ENV] = attempt_path
    environment[QUALIFICATION_ATTEMPT_HASH_ENV] = attempt_hash
    environment[QUALIFICATION_LOG_PATH_ENV] = os.devnull
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _validate_ledger_record(
    record: Any,
    *,
    sequence: int,
    previous_hash: str | None,
    registration: OutcomeEvidenceRegistration,
    run_lock_hash: str,
) -> None:
    if not isinstance(record, Mapping):
        raise OutcomeEvidenceRunnerError("ledger record must be an object")
    expected_fields = {
        "created_unix_ns",
        "event",
        "payload",
        "previous_record_hash",
        "record_hash",
        "registration_hash",
        "run_lock_hash",
        "schema_version",
        "sequence",
        "session_id",
        "slot_number",
        "study_id",
    }
    if set(record) != expected_fields:
        raise OutcomeEvidenceRunnerError("ledger record fields mismatch")
    if record["schema_version"] != LEDGER_SCHEMA_VERSION:
        raise OutcomeEvidenceRunnerError("ledger schema_version mismatch")
    if type(record["sequence"]) is not int or record["sequence"] != sequence:
        raise OutcomeEvidenceRunnerError("ledger sequence mismatch")
    if record["previous_record_hash"] != previous_hash:
        raise OutcomeEvidenceRunnerError("ledger hash chain mismatch")
    if record["study_id"] != registration.study_id:
        raise OutcomeEvidenceRunnerError("ledger study_id mismatch")
    if record["registration_hash"] != registration.registration_hash:
        raise OutcomeEvidenceRunnerError("ledger registration hash mismatch")
    if record["run_lock_hash"] != run_lock_hash:
        raise OutcomeEvidenceRunnerError("ledger run lock mismatch")
    if type(record["created_unix_ns"]) is not int or record["created_unix_ns"] <= 0:
        raise OutcomeEvidenceRunnerError("ledger timestamp is invalid")
    if not isinstance(record["event"], str) or not isinstance(
        record["payload"], Mapping
    ):
        raise OutcomeEvidenceRunnerError("ledger event or payload is invalid")
    if record["event"] in {"slot_started", "slot_terminal"}:
        slot_number = record["slot_number"]
        if type(slot_number) is not int or not (
            1 <= slot_number <= len(registration.slots)
        ):
            raise OutcomeEvidenceRunnerError("ledger slot identity is invalid")
        registered_slot = registration.slots[slot_number - 1]
        if record["session_id"] != registered_slot.session_id:
            raise OutcomeEvidenceRunnerError(
                "ledger session identity differs from registration"
            )
    elif record["event"] in {"study_started", "global_stop"}:
        if record["slot_number"] is not None or record["session_id"] is not None:
            raise OutcomeEvidenceRunnerError(
                "non-slot ledger event contains a session identity"
            )
    else:
        raise OutcomeEvidenceRunnerError(
            f"unsupported ledger event: {record['event']}"
        )
    payload = record["payload"]
    if record["event"] == "study_started":
        if payload != {"slot_count": len(registration.slots)}:
            raise OutcomeEvidenceRunnerError("study_started payload mismatch")
    elif record["event"] == "slot_started":
        if set(payload) not in (set(), {"marker_start_count"}):
            raise OutcomeEvidenceRunnerError("slot_started payload fields mismatch")
        if "marker_start_count" in payload and (
            type(payload["marker_start_count"]) is not int
            or payload["marker_start_count"] < 0
        ):
            raise OutcomeEvidenceRunnerError(
                "slot_started marker_start_count is invalid"
            )
    elif record["event"] == "slot_terminal":
        required_payload_fields = {
            "complete_trajectories",
            "marker_end_count",
            "marker_start_count",
            "process_exit_code",
            "terminal_status",
        }
        actual_payload_fields = set(payload)
        if not required_payload_fields.issubset(actual_payload_fields) or not (
            actual_payload_fields <= required_payload_fields | {"reason"}
        ):
            raise OutcomeEvidenceRunnerError("slot_terminal payload fields mismatch")
        complete = _bounded_count(payload["complete_trajectories"])
        _marker_bounds(
            payload["marker_start_count"],
            payload["marker_end_count"],
            complete_trajectories=complete,
        )
        exit_code = payload["process_exit_code"]
        if exit_code is not None and type(exit_code) is not int:
            raise OutcomeEvidenceRunnerError("process_exit_code is invalid")
        expected_status = (
            "completed" if exit_code == 0 and complete == 25 else "interrupted"
        )
        if payload["terminal_status"] != expected_status:
            raise OutcomeEvidenceRunnerError("terminal_status contradicts evidence")
        if "reason" in payload and (
            not isinstance(payload["reason"], str) or not payload["reason"].strip()
        ):
            raise OutcomeEvidenceRunnerError("terminal interruption reason is invalid")
        if exit_code is None and "reason" not in payload:
            raise OutcomeEvidenceRunnerError(
                "missing reason for terminal record without an exit code"
            )
    else:
        if set(payload) != {"reason"} or not isinstance(
            payload.get("reason"), str
        ) or not payload["reason"].strip():
            raise OutcomeEvidenceRunnerError("global_stop payload is invalid")
    supplied_hash = record["record_hash"]
    if not isinstance(supplied_hash, str) or not _is_lower_hex(
        supplied_hash, _SHA256_LENGTH
    ):
        raise OutcomeEvidenceRunnerError("ledger record hash is invalid")
    if supplied_hash != _record_hash(record):
        raise OutcomeEvidenceRunnerError("ledger record hash mismatch")


def _record_hash(record: Mapping[str, Any]) -> str:
    hash_input = dict(record)
    hash_input["record_hash"] = None
    return hashlib.sha256(_canonical_json(hash_input).encode("utf-8")).hexdigest()


def _publish_text_once(path: Path, text: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        descriptor, name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_path, path)
    except FileExistsError as exc:
        raise OutcomeEvidenceRunnerError(f"{label} already exists: {path}") from exc
    except OSError as exc:
        raise OutcomeEvidenceRunnerError(f"cannot publish {label}: {exc}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(f"value is not canonical JSON: {exc}") from exc


def _timestamp(value: int | None) -> int:
    timestamp = time.time_ns() if value is None else value
    if type(timestamp) is not int or timestamp <= 0:
        raise OutcomeEvidenceRunnerError("timestamp must be a positive integer")
    return timestamp


def _exact_int(value: Any, field: str) -> int:
    if type(value) is not int:
        raise OutcomeEvidenceRunnerError(f"{field} must be an exact integer")
    return value


def _bounded_count(value: Any) -> int:
    count = _exact_int(value, "complete_trajectories")
    if count < 0 or count > 25:
        raise OutcomeEvidenceRunnerError(
            "complete_trajectories must be between 0 and 25"
        )
    return count


def _marker_bounds(
    start: Any,
    end: Any,
    *,
    complete_trajectories: int,
) -> tuple[int | None, int | None]:
    if start is None and end is None:
        return None, None
    if type(start) is not int or type(end) is not int or start < 0 or end < start:
        raise OutcomeEvidenceRunnerError("AI marker bounds are invalid")
    if end - start != complete_trajectories:
        raise OutcomeEvidenceRunnerError(
            "AI marker bounds differ from complete_trajectories"
        )
    return start, end


def _required_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _is_lower_hex(value, _SHA256_LENGTH):
        raise OutcomeEvidenceRunnerError(f"{field} must be a SHA-256 hash")
    return value


def _is_lower_hex(value: str, length: int) -> bool:
    return len(value) == length and all(
        character in "0123456789abcdef" for character in value
    )


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise OutcomeEvidenceRunnerError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise OutcomeEvidenceRunnerError(f"invalid JSON constant: {value}")


def _load_run_lock_record(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceRunnerError(f"cannot load run lock: {exc}") from exc
    if not isinstance(payload, dict):
        raise OutcomeEvidenceRunnerError("run lock must be an object")
    return payload


def _ledger_path(registration: OutcomeEvidenceRegistration) -> Path:
    return Path(registration.artifact_root) / "study-ledger.jsonl"


def _run_lock_path(registration: OutcomeEvidenceRegistration) -> Path:
    return Path(registration.artifact_root) / "run-lock.json"


def _blocked_monitor_run_lock(
    registration: OutcomeEvidenceRegistration,
    ledger: StudyLedger,
) -> dict[str, Any]:
    return {
        "registration": {"canonical_hash": registration.registration_hash},
        "run_lock_hash": ledger.run_lock_hash,
        "source": {"commit": "0" * _GIT_COMMIT_LENGTH},
        "study_id": registration.study_id,
    }


def _load_runner_registration(
    registration_path: Path,
) -> OutcomeEvidenceRegistration:
    registration = load_registration(registration_path)
    registered_root = Path(registration.repo_root).resolve()
    if registered_root != REPO_ROOT:
        raise OutcomeEvidenceRunnerError(
            "registration repo_root does not match the runner checkout: "
            f"registered={registered_root}, runner={REPO_ROOT}"
        )
    return registration


def _require_launchable_runner_registration(
    registration: OutcomeEvidenceRegistration,
) -> OutcomeEvidenceRegistration:
    try:
        return require_launchable_registration(registration)
    except OutcomeEvidenceRegistrationError as exc:
        raise OutcomeEvidenceRunnerError(str(exc)) from exc


def _start_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    registration = _require_launchable_runner_registration(registration)
    command = _registered_command(registration)
    run_lock = create_run_lock(
        registration_path=registration_path,
        lock_path=_run_lock_path(registration),
        repo_root=registration.repo_root,
        child_command=command,
    )
    ledger = StudyLedger(
        path=_ledger_path(registration),
        registration=registration,
        run_lock_hash=run_lock["run_lock_hash"],
    )
    ledger.initialize()
    try:
        for slot in registration.slots:
            write_slot_config_once(
                build_slot_launch(registration, run_lock, slot.slot_number)
            )
    except Exception as exc:
        ledger.global_stop(
            reason=f"registered config publication failed: {type(exc).__name__}: {exc}"
        )
        raise
    return run_lock


def _dry_run_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    command = _registered_command(registration)
    run_lock_path = _run_lock_path(registration)
    ledger_path = _ledger_path(registration)
    if run_lock_path.exists() or ledger_path.exists():
        ledger = StudyLedger.open_existing(
            path=ledger_path,
            registration=registration,
        )
        run_lock = dict(
            validate_run_lock_or_stop(
                ledger,
                validator=lambda: validate_run_lock(
                    lock_path=run_lock_path,
                    registration_path=registration_path,
                    repo_root=registration.repo_root,
                    child_command=command,
                ),
            )
        )
    else:
        source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=registration.repo_root,
            text=True,
            encoding="utf-8",
        ).strip().lower()
        run_lock = {
            "registration": {"canonical_hash": registration.registration_hash},
            "run_lock_hash": "0" * 64,
            "source": {"commit": source_commit},
            "study_id": registration.study_id,
        }
    launches = [
        build_slot_launch(registration, run_lock, slot.slot_number)
        for slot in registration.slots
    ]
    handshake_rules = registration_handshake_rules(registration)
    return {
        "launch_count": len(launches),
        "launches": [
            {
                "command": list(launch.command),
                "config_path": launch.config_path,
                "config_record": dict(launch.config_record),
                "environment": dict(launch.environment),
                "handshake": _dry_run_handshake_record(
                    launch,
                    handshake_rules,
                ),
                "session_id": launch.session_id,
                "slot_number": launch.slot_number,
            }
            for launch in launches
        ],
        "study_id": registration.study_id,
    }


def _dry_run_handshake_record(
    launch: RegisteredSlotLaunch,
    rules: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if rules is None:
        return None
    paths = _handshake_paths_from_rules(
        config_path=launch.config_path,
        session_id=launch.session_id,
        rules=rules,
    )
    return {
        "attempt_path": str(paths.attempt),
        "protocol_version": rules["protocol_version"],
        "readiness_timeout_seconds": rules["readiness_timeout_seconds"],
        "ready_path": str(paths.ready),
        "release_path": str(paths.release),
        "release_timeout_seconds": rules["release_timeout_seconds"],
    }


def _run_next_command(registration_path: Path) -> dict[str, Any]:
    if QUALIFICATION_ATTEMPT_HASH_ENV in os.environ:
        raise OutcomeEvidenceRunnerError(
            "run-next refuses ambient qualification environment"
        )
    registration = _load_runner_registration(registration_path)
    registration = _require_launchable_runner_registration(registration)
    command = _registered_command(registration)
    run_lock_path = _run_lock_path(registration)
    ledger = StudyLedger.open_existing(
        path=_ledger_path(registration),
        registration=registration,
    )
    marker_path = (
        Path(registration.checkpoint_root).parent / "runs" / "ai_games.txt"
    )
    _recover_active_slot_after_host_failure(
        ledger=ledger,
        marker_path=marker_path,
    )
    run_lock = validate_run_lock_or_stop(
        ledger,
        validator=lambda: validate_run_lock(
            lock_path=run_lock_path,
            registration_path=registration_path,
            repo_root=registration.repo_root,
            child_command=command,
        ),
    )
    slot = ledger.next_slot()
    launch = build_slot_launch(registration, run_lock, slot.slot_number)
    config_path = Path(launch.config_path)
    if not config_path.exists():
        raise OutcomeEvidenceRunnerError(
            f"registered slot config is missing: {config_path}"
        )
    def process_starter(
        _launch: RegisteredSlotLaunch,
        child_environment: Mapping[str, str],
    ) -> subprocess.Popen:
        environment = os.environ.copy()
        environment.update(child_environment)
        return subprocess.Popen(
            list(launch.command),
            env=environment,
            cwd=str(Path(registration.checkpoint_root).parent),
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    return execute_handshaken_registered_slot(
        ledger=ledger,
        launch=launch,
        marker_path=marker_path,
        process_starter=process_starter,
        preclaim_validator=lambda: validate_run_lock(
            lock_path=run_lock_path,
            registration_path=registration_path,
            repo_root=registration.repo_root,
            child_command=command,
        ),
    )


def _qualify_command(
    registration_path: Path,
    request_path: Path,
    request_hash: str,
    request_file_sha256: str,
    request_size: int,
    review_commit: str,
) -> dict[str, Any]:
    registration = _load_qualification_registration(registration_path)
    checkpoint_root = _qualification_require_no_follow_path(
        registration.checkpoint_root,
        "checkpoint root",
        expected_kind="directory",
        allow_missing=True,
    )
    game_directory = checkpoint_root.parent

    def process_starter(
        command: Sequence[str],
        child_environment: Mapping[str, str],
    ) -> subprocess.Popen:
        return subprocess.Popen(
            list(command),
            env=dict(child_environment),
            cwd=str(game_directory),
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    return execute_prelock_qualification(
        registration_path=registration_path,
        request_path=request_path,
        expected_request_hash=request_hash,
        expected_review_commit=review_commit,
        expected_request_file_sha256=request_file_sha256,
        expected_request_size=request_size,
        process_starter=process_starter,
        qualification_launch_command=tuple(sys.orig_argv),
    )


def _monitor_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    command = _registered_command(registration)
    run_lock_path = _run_lock_path(registration)
    ledger = StudyLedger.open_existing(
        path=_ledger_path(registration),
        registration=registration,
    )
    snapshot = ledger.snapshot()
    stop_reason = (
        snapshot["global_stop"].get("reason")
        if isinstance(snapshot["global_stop"], Mapping)
        else None
    )
    run_lock_valid = not (
        isinstance(stop_reason, str)
        and stop_reason.startswith("run lock validation failed:")
    )
    run_lock: dict[str, Any] | None = None
    if snapshot["global_stop"] is None:
        try:
            run_lock = dict(
                validate_run_lock_or_stop(
                    ledger,
                    validator=lambda: validate_run_lock(
                        lock_path=run_lock_path,
                        registration_path=registration_path,
                        repo_root=registration.repo_root,
                        child_command=command,
                    ),
                )
            )
        except OutcomeEvidenceRunnerError:
            run_lock_valid = False
            snapshot = ledger.snapshot()
    if run_lock is None:
        try:
            candidate_run_lock = _load_run_lock_record(run_lock_path)
            candidate_binding = _validate_run_lock_binding(
                registration,
                candidate_run_lock,
            )
            if candidate_binding["run_lock_hash"] != ledger.run_lock_hash:
                raise OutcomeEvidenceRunnerError(
                    "monitor run lock differs from the ledger binding"
                )
            run_lock = candidate_run_lock
        except OutcomeEvidenceRunnerError:
            run_lock_valid = False
            run_lock = _blocked_monitor_run_lock(registration, ledger)
    observations = collect_structural_observations(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=snapshot,
    )
    monitor = build_blinded_monitor(
        registration=registration,
        run_lock=run_lock,
        ledger_snapshot=snapshot,
        structural_observations=observations,
        run_lock_valid=run_lock_valid,
    )
    artifact_root = Path(registration.artifact_root)
    write_blinded_monitor_artifacts(
        monitor,
        json_path=artifact_root / "blinded-monitor.json",
        markdown_path=artifact_root / "blinded-monitor.md",
    )
    return monitor


def _finalize_gate_command(registration_path: Path) -> dict[str, Any]:
    registration = _load_runner_registration(registration_path)
    ledger = StudyLedger.open_existing(
        path=_ledger_path(registration),
        registration=registration,
    )
    snapshot = ledger.snapshot()
    if not (
        snapshot["all_slots_terminal"] or snapshot["global_stop"] is not None
    ):
        raise OutcomeEvidenceRunnerError(
            "finalization requires all slots terminal or a global stop"
        )
    if snapshot["global_stop"] is not None:
        return finalize_registered_integrity_stop(
            registration,
            run_lock_hash=ledger.run_lock_hash,
            ledger_snapshot=snapshot,
        )

    command = _registered_command(registration)
    try:
        run_lock = validate_run_lock_or_stop(
            ledger,
            validator=lambda: validate_run_lock(
                lock_path=_run_lock_path(registration),
                registration_path=registration_path,
                repo_root=registration.repo_root,
                child_command=command,
            ),
        )
    except OutcomeEvidenceRunnerError:
        snapshot = ledger.snapshot()
        if snapshot["global_stop"] is None:
            raise
        return finalize_registered_integrity_stop(
            registration,
            run_lock_hash=ledger.run_lock_hash,
            ledger_snapshot=snapshot,
        )
    snapshot = ledger.snapshot()
    if snapshot["global_stop"] is not None:
        return finalize_registered_integrity_stop(
            registration,
            run_lock_hash=ledger.run_lock_hash,
            ledger_snapshot=snapshot,
        )
    sessions = collect_registered_session_evidence(
        registration,
        run_lock=run_lock,
        ledger_snapshot=snapshot,
    )
    run_lock_hash = str(run_lock["run_lock_hash"])
    pool = build_registered_pool(
        registration,
        run_lock_hash=run_lock_hash,
        ledger_snapshot=snapshot,
        sessions=sessions,
    )
    return finalize_registered_outcome_evidence(
        registration,
        run_lock_hash=run_lock_hash,
        ledger_snapshot=snapshot,
        pool=pool,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Operate the registered non-combat outcome-evidence study."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    for name in ("start", "dry-run", "run-next", "monitor", "finalize"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--registration", type=Path, required=True)
    qualification_parser = subparsers.add_parser("qualify")
    qualification_parser.add_argument("--registration", type=Path, required=True)
    qualification_parser.add_argument("--request", type=Path, required=True)
    qualification_parser.add_argument("--request-hash", required=True)
    qualification_parser.add_argument("--request-file-sha256", required=True)
    qualification_parser.add_argument("--request-size", type=int, required=True)
    qualification_parser.add_argument("--review-commit", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.subcommand == "start":
            result = _start_command(args.registration)
        elif args.subcommand == "dry-run":
            result = _dry_run_command(args.registration)
        elif args.subcommand == "run-next":
            result = _run_next_command(args.registration)
        elif args.subcommand == "qualify":
            result = _qualify_command(
                args.registration,
                args.request,
                args.request_hash,
                args.request_file_sha256,
                args.request_size,
                args.review_commit,
            )
        elif args.subcommand == "monitor":
            result = _monitor_command(args.registration)
        else:
            result = _finalize_gate_command(args.registration)
        if args.subcommand != "qualify":
            output_stream = (
                sys.stderr if args.subcommand == "run-next" else sys.stdout
            )
            print(_canonical_json(result), file=output_stream)
        return 0
    except Exception as exc:
        if args.subcommand != "qualify":
            print(f"[outcome-evidence] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
