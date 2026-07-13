"""Explicit live wiring for bounded non-combat exploration sessions."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from spirecomm.ai.noncombat_exploration import (
    ExplorationConfigurationError,
    ExplorationPersistenceError,
    NonCombatExplorationController,
    ProposalAdapterResult,
    build_card_reward_proposal,
    build_event_shadow_proposal,
    build_route_shadow_proposal,
    build_shop_proposal,
    create_exploration_session_manifest,
    load_exploration_config_from_env,
)
from spirecomm.spire.screen import ScreenType


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GitSourceState:
    commit: str
    tracked_clean: bool
    tracked_status: str


class NonCombatExplorationRuntime:
    """Wrap an existing Current callback without changing its default path."""

    def __init__(
        self,
        controller: NonCombatExplorationController,
        *,
        manifest: Mapping[str, Any],
        agent_type: str,
    ):
        self.controller = controller
        self.manifest = dict(manifest)
        self.agent_type = str(agent_type)

    def begin_game(self, run_token: str) -> str:
        trajectory_id = self.controller.begin_trajectory(run_token)
        logger.info(
            "[NONCOMBAT_EXPLORATION] begin trajectory=%s session=%s",
            trajectory_id,
            self.controller.config.session_id,
        )
        return trajectory_id

    def end_game(self, game: Any = None) -> Optional[dict[str, Any]]:
        if self.controller.trajectory_session_id is None:
            return None
        if game is not None and self.controller.pending_decision_id is not None:
            self.controller.resolve_pending(game)
        resolution = self.controller.end_trajectory(game)
        logger.info(
            "[NONCOMBAT_EXPLORATION] end session=%s terminal_resolution=%s",
            self.controller.config.session_id,
            resolution.get("status") if resolution else "none",
        )
        return resolution

    def wrap_state_callback(
        self,
        current_callback: Callable[[Any], Any],
        *,
        policy_agent: Any = None,
    ) -> Callable[[Any], Any]:
        def wrapped(game: Any) -> Any:
            resolution_failed = False
            if self.controller.pending_decision_id is not None:
                try:
                    resolution = self.controller.resolve_pending(game)
                    if resolution is not None:
                        logger.info(
                            "[NONCOMBAT_EXPLORATION] resolve decision=%s status=%s reason=%s",
                            resolution["decision_id"],
                            resolution["status"],
                            resolution["reason"],
                        )
                except Exception as exc:
                    resolution_failed = True
                    logger.error(
                        "[NONCOMBAT_EXPLORATION] resolution failed closed: %s",
                        exc,
                    )

            transaction_category = _active_transaction_category(
                game,
                self.controller.config,
            )
            transaction = None
            if transaction_category is not None:
                if not _supports_policy_transaction(policy_agent):
                    logger.error(
                        "[NONCOMBAT_EXPLORATION] policy has no side-effect "
                        "transaction; failing closed to Current"
                    )
                    return current_callback(game)
                try:
                    transaction = policy_agent.begin_noncombat_exploration_preview(
                        game,
                        transaction_category,
                    )
                except Exception as exc:
                    logger.error(
                        "[NONCOMBAT_EXPLORATION] preview start failed closed: %s",
                        exc,
                    )
                    return current_callback(game)

            try:
                current_action = current_callback(game)
            except Exception:
                if transaction is not None:
                    try:
                        policy_agent.abort_noncombat_exploration_preview(transaction)
                    except Exception as exc:
                        logger.error(
                            "[NONCOMBAT_EXPLORATION] preview abort failed: %s",
                            exc,
                        )
                raise

            if transaction is not None:
                try:
                    transaction = policy_agent.finish_noncombat_exploration_preview(
                        transaction
                    )
                except Exception as exc:
                    logger.error(
                        "[NONCOMBAT_EXPLORATION] preview rollback failed closed: %s",
                        exc,
                    )
                    return current_action

            def commit_action(action: Any, *, baseline_selected: bool) -> Any:
                if transaction is None:
                    return action
                try:
                    committed = policy_agent.commit_noncombat_exploration_action(
                        transaction,
                        game,
                        transaction_category,
                        action,
                        baseline_selected=baseline_selected,
                    )
                    return action if committed is None else committed
                except Exception as exc:
                    logger.error(
                        "[NONCOMBAT_EXPLORATION] selected-action commit failed "
                        "closed to Current: %s",
                        exc,
                    )
                    if not baseline_selected:
                        try:
                            policy_agent.commit_noncombat_exploration_action(
                                transaction,
                                game,
                                transaction_category,
                                current_action,
                                baseline_selected=True,
                            )
                        except Exception as restore_exc:
                            logger.error(
                                "[NONCOMBAT_EXPLORATION] baseline-state restore "
                                "failed: %s",
                                restore_exc,
                            )
                    return current_action

            if current_action is None or resolution_failed:
                return commit_action(current_action, baseline_selected=True)
            try:
                adapter = _build_adapter(
                    game,
                    current_action,
                    policy_agent=policy_agent,
                )
                if adapter is None:
                    return commit_action(current_action, baseline_selected=True)
                if not adapter.execution_eligible:
                    if adapter.proposal is not None:
                        logger.debug(
                            "[NONCOMBAT_EXPLORATION] shadow category=%s state=%s candidates=%s",
                            adapter.category,
                            adapter.proposal.state_hash,
                            adapter.proposal.candidate_ids,
                        )
                    return commit_action(current_action, baseline_selected=True)
                result = self.controller.consider(adapter, game)
            except Exception as exc:
                logger.error(
                    "[NONCOMBAT_EXPLORATION] proposal failed closed to Current: %s",
                    exc,
                )
                return commit_action(current_action, baseline_selected=True)
            if result.known_propensity:
                logger.info(
                    "[NONCOMBAT_EXPLORATION] proposed decision=%s category=%s selected=%s probability=%s/%s",
                    result.decision_id,
                    adapter.category,
                    result.selected_action_id,
                    result.selection.selected_probability_numerator,
                    result.selection.selected_probability_denominator,
                )
            else:
                logger.warning(
                    "[NONCOMBAT_EXPLORATION] Current fallback category=%s reason=%s",
                    adapter.category,
                    result.fallback_reason,
                )
            alternative_selected = bool(
                result.known_propensity
                and adapter.proposal is not None
                and result.selected_action_id
                == adapter.proposal.alternative_action_id
            )
            return commit_action(
                result.action,
                baseline_selected=not alternative_selected,
            )

        return wrapped


def initialize_noncombat_exploration_runtime(
    *,
    environ: Optional[Mapping[str, str]] = None,
    repo_root: Path,
    command: list[str] | tuple[str, ...],
    python_executable: str,
    training: bool,
    agent_type: str,
    isolation_hashes: Optional[Mapping[str, Any]] = None,
) -> Optional[NonCombatExplorationRuntime]:
    """Validate and publish an explicit session, or stay completely inert."""

    config = load_exploration_config_from_env(environ)
    if config is None:
        return None
    if training:
        raise ExplorationConfigurationError(
            "non-combat exploration is a no-training evaluation mode"
        )
    source_state = inspect_git_source(Path(repo_root))
    if not source_state.tracked_clean:
        raise ExplorationPersistenceError(
            "tracked source is dirty; refusing exploration startup: "
            + source_state.tracked_status
        )
    if source_state.commit.lower() != config.source_commit.lower():
        raise ExplorationPersistenceError(
            "source commit mismatch: "
            f"config={config.source_commit} actual={source_state.commit}"
        )
    if isolation_hashes is None:
        isolation_hashes = capture_default_isolation_hashes(Path(repo_root))
    manifest = create_exploration_session_manifest(
        config,
        source_clean=True,
        python_executable=python_executable,
        command=command,
        isolation_hashes=isolation_hashes,
    )
    controller = NonCombatExplorationController(config)
    logger.info(
        "[NONCOMBAT_EXPLORATION] enabled session=%s agent=%s rates=%s budget=%s",
        config.session_id,
        agent_type,
        dict(config.category_rates_bps),
        config.per_run_alternative_budget,
    )
    return NonCombatExplorationRuntime(
        controller,
        manifest=manifest,
        agent_type=agent_type,
    )


def inspect_git_source(repo_root: Path) -> GitSourceState:
    root = Path(repo_root).resolve()
    commit_result = _run_git(root, "rev-parse", "HEAD")
    status_result = _run_git(
        root,
        "status",
        "--porcelain",
        "--untracked-files=no",
    )
    commit = commit_result.strip().lower()
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ExplorationPersistenceError(
            f"git returned an invalid source commit: {commit!r}"
        )
    tracked_status = status_result.strip()
    return GitSourceState(
        commit=commit,
        tracked_clean=not tracked_status,
        tracked_status=tracked_status,
    )


def _run_git(repo_root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise ExplorationPersistenceError(f"unable to run git: {exc}") from exc
    if result.returncode != 0:
        error = (result.stderr or result.stdout).strip()
        raise ExplorationPersistenceError(
            f"git {' '.join(arguments)} failed: {error}"
        )
    return result.stdout


def capture_default_isolation_hashes(repo_root: Path) -> dict[str, Any]:
    paths: list[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        paths.append(
            Path(local_app_data)
            / "ModTheSpire"
            / "CommunicationMod"
            / "config.properties"
        )
    checkpoint_roots = {Path.cwd() / "checkpoints", Path(repo_root) / "checkpoints"}
    for checkpoint_root in checkpoint_roots:
        for pattern in ("rl_combat_model_*.pth", "rl_model_*.pth"):
            paths.extend(sorted(checkpoint_root.glob(pattern)))
    return {
        str(path.resolve()): _file_fingerprint(path)
        for path in sorted(set(paths), key=lambda item: str(item).lower())
    }


def _file_fingerprint(path: Path) -> dict[str, Any]:
    resolved = Path(path).resolve()
    if not resolved.exists():
        return {"exists": False}
    if not resolved.is_file():
        return {"exists": True, "is_file": False}
    try:
        stat = resolved.stat()
        digest = hashlib.sha256()
        with resolved.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        semantic_sha256 = (
            _properties_semantic_sha256(resolved)
            if resolved.suffix.lower() == ".properties"
            else None
        )
    except OSError as exc:
        raise ExplorationPersistenceError(
            f"unable to fingerprint isolation path {resolved}: {exc}"
        ) from exc
    fingerprint = {
        "exists": True,
        "is_file": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest.hexdigest(),
    }
    if semantic_sha256 is not None:
        fingerprint["semantic_sha256"] = semantic_sha256
    return fingerprint


def _properties_semantic_sha256(path: Path) -> str:
    properties: dict[str, str] = {}
    content = path.read_text(encoding="iso-8859-1")
    natural_lines = (
        content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    )
    for logical_line in _java_properties_logical_lines(natural_lines):
        parsed = _parse_java_property(logical_line)
        if parsed is None:
            continue
        key, value = parsed
        properties[key] = value
    payload = (
        json.dumps(
            properties,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _java_properties_logical_lines(lines: list[str]):
    pending = ""
    continuing = False
    for natural_line in lines:
        if not continuing and natural_line.lstrip(" \t\f").startswith(("#", "!")):
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


def _parse_java_property(line: str) -> Optional[tuple[str, str]]:
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
        _decode_java_property_escapes(content[:key_end]),
        _decode_java_property_escapes(content[value_start:]),
    )


def _decode_java_property_escapes(value: str) -> str:
    decoded: list[str] = []
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
            raise ExplorationPersistenceError(
                "invalid trailing escape in Java properties file"
            )
        escaped = value[index]
        if escaped == "u":
            digits = value[index + 1 : index + 5]
            if len(digits) != 4 or any(
                digit not in "0123456789abcdefABCDEF" for digit in digits
            ):
                raise ExplorationPersistenceError(
                    "invalid Unicode escape in Java properties file"
                )
            decoded.append(chr(int(digits, 16)))
            index += 5
            continue
        decoded.append(escapes.get(escaped, escaped))
        index += 1
    return "".join(decoded)


def _build_adapter(
    game: Any,
    current_action: Any,
    *,
    policy_agent: Any,
) -> Optional[ProposalAdapterResult]:
    screen_type = getattr(game, "screen_type", None)
    if screen_type == ScreenType.CARD_REWARD:
        return build_card_reward_proposal(game, current_action)
    if screen_type == ScreenType.SHOP_SCREEN:
        return build_shop_proposal(
            game,
            current_action,
            agent=_shop_policy_agent(policy_agent),
        )
    if screen_type == ScreenType.EVENT:
        return build_event_shadow_proposal(game, current_action)
    if screen_type == ScreenType.MAP:
        return build_route_shadow_proposal(game, current_action)
    return None


def _shop_policy_agent(agent: Any) -> Any:
    fallback = getattr(agent, "fallback_agent", None)
    return fallback if fallback is not None else agent


def _active_transaction_category(game: Any, config: Any) -> Optional[str]:
    screen_type = getattr(game, "screen_type", None)
    if screen_type == ScreenType.CARD_REWARD:
        category = "card_reward"
    elif screen_type == ScreenType.SHOP_SCREEN:
        category = "shop"
    else:
        return None
    if category not in config.enabled_categories or config.rate_bps(category) == 0:
        return None
    return category


def _supports_policy_transaction(agent: Any) -> bool:
    if agent is None:
        return False
    return all(
        callable(getattr(agent, name, None))
        for name in (
            "begin_noncombat_exploration_preview",
            "finish_noncombat_exploration_preview",
            "abort_noncombat_exploration_preview",
            "commit_noncombat_exploration_action",
        )
    )
