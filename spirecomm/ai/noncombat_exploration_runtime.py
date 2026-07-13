"""Explicit live wiring for bounded non-combat exploration sessions."""

from __future__ import annotations

import hashlib
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

            current_action = current_callback(game)
            if current_action is None or resolution_failed:
                return current_action
            try:
                adapter = _build_adapter(
                    game,
                    current_action,
                    policy_agent=policy_agent,
                )
                if adapter is None:
                    return current_action
                if not adapter.execution_eligible:
                    if adapter.proposal is not None:
                        logger.debug(
                            "[NONCOMBAT_EXPLORATION] shadow category=%s state=%s candidates=%s",
                            adapter.category,
                            adapter.proposal.state_hash,
                            adapter.proposal.candidate_ids,
                        )
                    return current_action
                result = self.controller.consider(adapter, game)
            except Exception as exc:
                logger.error(
                    "[NONCOMBAT_EXPLORATION] proposal failed closed to Current: %s",
                    exc,
                )
                return current_action
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
            return result.action

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
    except OSError as exc:
        raise ExplorationPersistenceError(
            f"unable to fingerprint isolation path {resolved}: {exc}"
        ) from exc
    return {
        "exists": True,
        "is_file": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest.hexdigest(),
    }


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
