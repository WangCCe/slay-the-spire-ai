import argparse
import importlib.machinery
import os
import sys
import logging
import math
import glob
import shutil
import stat
import time
import re
from pathlib import Path
from logging.handlers import RotatingFileHandler
from importlib.util import find_spec

QUALIFICATION_ATTEMPT_HASH_ENV = (
    "STS_OUTCOME_EVIDENCE_QUALIFICATION_ATTEMPT_HASH"
)

if QUALIFICATION_ATTEMPT_HASH_ENV in os.environ:
    if not sys.flags.isolated or not sys.flags.no_site:
        sys.stderr.write(
            "qualification child requires isolated no-site Python startup "
            "(-I -S)\n"
        )
        raise SystemExit(2)
    sys.dont_write_bytecode = True
    sys.pycache_prefix = os.path.join(
        os.devnull,
        "sts-qualification-pycache",
    )

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def _qualification_install_source_only_repo_imports(repo_root):
    lexical_root = os.path.normcase(os.path.abspath(repo_root))

    def is_repo_path(path_value):
        try:
            lexical_path = os.path.normcase(
                os.path.abspath(os.fspath(path_value))
            )
            return os.path.commonpath((lexical_root, lexical_path)) == lexical_root
        except (OSError, TypeError, ValueError):
            return False

    class NoFollowSourceLoader(importlib.machinery.SourceFileLoader):
        def get_data(self, path_value):
            lexical_path = os.path.abspath(path_value)
            if not is_repo_path(lexical_path):
                raise OSError(
                    "qualification repository loader refuses bytecode cache"
                )
            current_path = Path(Path(lexical_path).anchor)
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

    def source_only_path_hook(path_value):
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


if QUALIFICATION_ATTEMPT_HASH_ENV in os.environ:
    _qualification_install_source_only_repo_imports(_REPO_ROOT)

if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from spirecomm.communication.coordinator import Coordinator
from spirecomm.ai.agent import SimpleAgent, OptimizedAgent, OPTIMIZED_AI_AVAILABLE
from spirecomm.spire.character import PlayerClass

class QualificationChildComplete(Exception):
    """Stop a released qualification child before exploration and agents."""

def _optional_dependency_available(name):
    return find_spec(name) is not None


RL_AVAILABLE = (
    _optional_dependency_available("numpy")
    and _optional_dependency_available("torch")
)
RL_V2_AVAILABLE = RL_AVAILABLE
RLAgent = None
RLAgentV2 = None
create_rl_agent = None
CombatRLAgent = None
_RL_COMPONENTS_LOADED = False


def _load_rl_components():
    global RL_AVAILABLE
    global RL_V2_AVAILABLE
    global RLAgent
    global RLAgentV2
    global create_rl_agent
    global CombatRLAgent
    global _RL_COMPONENTS_LOADED

    if _RL_COMPONENTS_LOADED:
        return

    logging.info("Loading RL components...")
    try:
        from spirecomm.ai.rl import (
            RLAgent as loaded_rl_agent,
            RLAgentV2 as loaded_rl_agent_v2,
            create_agent as loaded_create_rl_agent,
            CombatRLAgent as loaded_combat_rl_agent,
        )
    except ImportError:
        RL_AVAILABLE = False
        RL_V2_AVAILABLE = False
        RLAgent = None
        RLAgentV2 = None
        create_rl_agent = None
        CombatRLAgent = None
    else:
        RLAgent = loaded_rl_agent
        RLAgentV2 = loaded_rl_agent_v2
        create_rl_agent = loaded_create_rl_agent
        CombatRLAgent = loaded_combat_rl_agent
        RL_AVAILABLE = (
            RLAgent is not None
            and create_rl_agent is not None
            and CombatRLAgent is not None
        )
        RL_V2_AVAILABLE = RLAgentV2 is not None
    finally:
        _RL_COMPONENTS_LOADED = True
        logging.info(
            "RL components loaded: rl_available=%s rl_v2_available=%s",
            RL_AVAILABLE,
            RL_V2_AVAILABLE,
        )

# Setup logging to file with rotation (all logs go to ai_debug.log)
# Note: We don't use StreamHandler because Communication Mod uses stdout for commands
# Log rotation: 10MB per file, keep 5 backup files (60MB total)
# Python 3.7 compatibility: force parameter not available, check if already configured
LOG_PATH = os.environ.get("STS_AI_LOG_FILE", "ai_debug.log")
LOG_LEVEL_NAME = os.environ.get("STS_AI_LOG_LEVEL", "DEBUG").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.DEBUG)
LOG_MAX_BYTES = int(os.environ.get("STS_AI_LOG_MAX_BYTES", str(10 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.environ.get("STS_AI_LOG_BACKUP_COUNT", "5"))
LOG_FILTER_NOISE = os.environ.get("STS_AI_LOG_FILTER_NOISE", "1") != "0"


class SafeRotatingFileHandler(RotatingFileHandler):
    """Rotating handler that avoids crashing on Windows file locks."""

    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            # If another process is holding the log file, switch to a new file.
            try:
                import time

                ts = time.strftime("%Y%m%d-%H%M%S")
                pid = os.getpid()
                base, ext = os.path.splitext(self.baseFilename)
                new_name = f"{base}_{ts}_{pid}{ext}"
                if self.stream:
                    self.stream.close()
                    self.stream = None
                self.baseFilename = os.path.abspath(new_name)
                self.mode = 'a'
                self.stream = self._open()
            except Exception:
                # Fall back to continuing without rotation if all else fails.
                if self.stream is None:
                    self.stream = self._open()


class NoiseFilter(logging.Filter):
    """Filter out high-frequency coordinator logs to reduce log volume."""

    def __init__(self, substrings):
        super().__init__()
        self.substrings = substrings

    def filter(self, record):
        msg = record.getMessage()
        return not any(sub in msg for sub in self.substrings)


def _create_log_handler():
    handler = SafeRotatingFileHandler(
        LOG_PATH,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8',
        mode='a'
    )
    if LOG_FILTER_NOISE:
        noisy = [
            "[RECEIVE_START]",
            "[RECEIVE_AFTER]",
            "[SEND_MESSAGE]",
            "[MAIN_LOOP] No immediate update",
            "[ACTION_QUEUE]",
        ]
        handler.addFilter(NoiseFilter(noisy))
    return handler


if not logging.getLogger().hasHandlers():
    handler = _create_log_handler()
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            handler,
        ],
    )
else:
    # Logging already configured, just add our rotating file handler if not present
    logger = logging.getLogger()
    has_rotating_handler = any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
    if not has_rotating_handler:
        rotating_handler = _create_log_handler()
        logger.addHandler(rotating_handler)


UNRECOVERABLE_RUN_ERROR_MARKERS = (
    "Game appears stuck",
    "Communication Mod not responding",
    "Communication Mod not ready",
    "Communication Mod connection lost",
    "Failed to start new game",
)


def is_unrecoverable_run_error(error):
    message = str(error)
    return any(marker in message for marker in UNRECOVERABLE_RUN_ERROR_MARKERS)


def find_latest_checkpoint():
    """
    Find the latest RL checkpoint file in the checkpoints directory.

    Returns:
        Path to the latest checkpoint file, or None if no checkpoints found
    """
    checkpoint_dir = "checkpoints"

    # Check if checkpoints directory exists
    if not os.path.exists(checkpoint_dir):
        return None

    # Find all checkpoint files matching the pattern rl_combat_model_ep*.pth
    pattern = os.path.join(checkpoint_dir, "rl_combat_model_ep*.pth")
    checkpoint_files = glob.glob(pattern)

    if not checkpoint_files:
        return None

    # Sort by modification time (most recent first)
    checkpoint_files.sort(key=os.path.getmtime, reverse=True)

    latest = checkpoint_files[0]
    logging.info(f"Found latest checkpoint: {latest}")
    logging.info(f"  Modified: {os.path.getmtime(latest)}")

    return latest


def archive_old_runs(character, keep=1000):
    """Archive older run files to keep the active runs directory small."""
    try:
        runs_root = Path("runs")
        runs_dir = runs_root / character
        if not runs_dir.exists():
            logging.warning(f"Runs directory not found: {runs_dir}")
            return 0, 0

        run_files = sorted(runs_dir.glob("*.run"), key=lambda p: p.stat().st_mtime)
        if len(run_files) <= keep:
            return 0, len(run_files)

        archive_root = runs_root.parent / "runs_archive"
        archive_dir = archive_root / character
        archive_dir.mkdir(parents=True, exist_ok=True)

        to_archive = run_files[:-keep]
        archived = 0
        for path in to_archive:
            dest = archive_dir / path.name
            if dest.exists():
                logging.warning(f"Archive destination exists, skipping: {dest}")
                continue
            try:
                shutil.move(str(path), str(dest))
                archived += 1
            except Exception as move_error:
                logging.warning(f"Failed to archive {path.name}: {move_error}")

        return archived, len(run_files) - archived
    except Exception as e:
        logging.warning(f"Run archiving failed: {e}")
        return 0, 0


def backup_latest_checkpoint(backup_dir, pattern):
    """Copy the latest checkpoint to a backup directory."""
    checkpoint_files = glob.glob(pattern)
    if not checkpoint_files:
        logging.warning("No existing checkpoints found for backup")
        return None

    checkpoint_files.sort(key=os.path.getmtime, reverse=True)
    latest = checkpoint_files[0]
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    base_name = os.path.basename(latest)
    backup_name = f"{base_name}.{timestamp}.bak"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        os.makedirs(backup_dir, exist_ok=True)
        shutil.copy2(latest, backup_path)
        logging.info(f"Checkpoint backup saved: {backup_path}")
        return backup_path
    except Exception as e:
        logging.warning(f"Checkpoint backup failed: {e}")
        return None


def get_training_checkpoint_suffix(agent, fallback_episode):
    """Build a checkpoint suffix that remains unique across bounded batches."""
    trainer = None
    if hasattr(agent, "trainer") and agent.trainer is not None:
        trainer = agent.trainer
    elif hasattr(agent, "rl_agent") and hasattr(agent.rl_agent, "trainer"):
        trainer = agent.rl_agent.trainer

    if trainer is not None:
        episode = getattr(trainer, "episode_count", fallback_episode)
        steps = getattr(trainer, "total_steps", 0)
        return f"ep{episode}_steps{steps}"
    return f"ep{fallback_episode}"


def log_decision_summary(summary, title="Game Summary"):
    """Log a decision summary without assuming every agent tracks every field."""
    total_decisions = summary.get("total_decisions", 0)
    combat_decisions = summary.get("combat_decisions", 0)
    card_rewards = summary.get("card_rewards", 0)
    avg_confidence = summary.get("avg_confidence", 0.0)

    logging.info(f"\n{title}:\n")
    logging.info(f"  Total Decisions: {total_decisions}\n")
    logging.info(f"  Combat Decisions: {combat_decisions}\n")
    logging.info(f"  Card Rewards: {card_rewards}\n")
    logging.info(f"  Avg Confidence: {avg_confidence:.2f}\n")


def load_seed_pool(seed_pool_path):
    """Load a seed pool file (one seed per line, # for comments)."""
    path = Path(seed_pool_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed pool file not found: {path}")

    seeds = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if not line:
            continue
        seeds.append(line)
    return seeds


def create_ready_coordinator(agent_type, *, force_input_thread=False):
    defer_input_thread = (
        agent_type in {"rl", "combat_rl"} and not force_input_thread
    )
    logging.info("Creating CommunicationMod coordinator")
    coordinator = Coordinator(start_input_thread=not defer_input_thread)
    logging.info("CommunicationMod coordinator created; signaling ready")
    coordinator.signal_ready()
    logging.info(
        "CommunicationMod ready signal queued; creating agent"
        " (stdin reader deferred=%s)",
        defer_input_thread,
    )
    return coordinator, defer_input_thread


RL_ADAPTIVE_ROUTE_ERROR = (
    "--elite-route adaptive is unsupported for --agent rl; "
    "adaptive routing requires a heuristic map owner"
)


def validate_agent_route_compatibility(agent_type, elite_mode):
    if agent_type == "rl" and str(elite_mode or "").lower() == "adaptive":
        raise ValueError(RL_ADAPTIVE_ROUTE_ERROR)


def create_agent(
    agent_type="auto",
    use_optimized=None,
    player_class=None,
    training=False,
    model_path=None,
    epsilon=0.0,
    elite_mode=None,
    rl_version=None,
    expert_mix_enabled=None,
    expert_mix_prob=None,
    expert_warmup_steps=None,
    parent_policy_anchor_weight=None,
    positive_energy_action_imitation_weight=None,
):
    """
    Create an agent instance.

    Args:
        agent_type: Type of agent ("simple", "optimized", "rl", "combat_rl", "auto")
        use_optimized: DEPRECATED - Use agent_type instead
        player_class: Player class (required for RL agent, optional for others)
        training: Whether RL agent should be in training mode
        model_path: Path to pre-trained RL model checkpoint
        epsilon: Exploration rate for non-training RL inference
        elite_mode: Elite routing mode ("conservative", "aggressive", or
            "adaptive", default: "aggressive"). Adaptive requires a heuristic
            map owner and is rejected for the full RL agent.
        rl_version: RL space version ("v1" or "v2"), defaults to STS_RL_VERSION or "v1"

    Returns:
        Agent instance (SimpleAgent, OptimizedAgent, RLAgent, or CombatRLAgent)
    """
    # Handle legacy use_optimized parameter
    if agent_type == "auto" and use_optimized is not None:
        agent_type = "optimized" if use_optimized else "simple"

    validate_agent_route_compatibility(agent_type, elite_mode)

    # Auto-detect: use optimized for Ironclad, simple for others
    if agent_type == "auto":
        if player_class == PlayerClass.IRONCLAD:
            agent_type = "optimized"
            logging.info("Auto-enabling OptimizedAgent for Ironclad")
        else:
            agent_type = "simple"

    if rl_version is None:
        rl_version = os.environ.get("STS_RL_VERSION", "v1")

    # Create combat RL agent (RL for combat, OptimizedAgent for everything else)
    if agent_type == "combat_rl":
        _load_rl_components()
        if str(rl_version).lower() == "v2":
            rl_ready = RL_V2_AVAILABLE
        else:
            rl_ready = RL_AVAILABLE

        if not rl_ready:
            logging.error("Combat RL agent requested but PyTorch/RL components not available")
            logging.error("Please install: pip install torch numpy")
            logging.error("Falling back to OptimizedAgent")
            return OptimizedAgent(chosen_class=player_class, elite_mode=elite_mode) if player_class and OPTIMIZED_AI_AVAILABLE else SimpleAgent(chosen_class=player_class, elite_mode=elite_mode)

        if player_class is None:
            logging.warning("Combat RL agent requires player_class, defaulting to IRONCLAD")
            player_class = PlayerClass.IRONCLAD

        if player_class != PlayerClass.IRONCLAD:
            logging.warning(f"Combat RL agent only supports IRONCLAD, got {player_class}")
            logging.warning("Falling back to OptimizedAgent")
            return OptimizedAgent(chosen_class=player_class, elite_mode=elite_mode) if OPTIMIZED_AI_AVAILABLE else SimpleAgent(chosen_class=player_class, elite_mode=elite_mode)

        try:
            logging.info(f"Creating Combat RL Agent (training={training})")

            # Auto-load latest checkpoint if in training mode and no model specified
            if training and model_path is None:
                auto_model_path = find_latest_checkpoint()
                if auto_model_path:
                    logging.info("Auto-loading latest checkpoint for continued training")
                    model_path = auto_model_path
                else:
                    logging.info("No existing checkpoints found, starting fresh training")

            agent = CombatRLAgent(
                player_class=player_class,
                training=training,
                model_path=model_path,
                epsilon=epsilon,
                elite_mode=elite_mode,
                rl_version=rl_version,
                expert_mix_enabled=expert_mix_enabled,
                expert_mix_prob=expert_mix_prob,
                expert_warmup_steps=expert_warmup_steps,
                parent_policy_anchor_weight=parent_policy_anchor_weight,
                positive_energy_action_imitation_weight=(
                    positive_energy_action_imitation_weight
                ),
            )
            logging.info(f"Combat RL Agent created successfully")
            logging.info(f"  State dim: {agent.rl_agent.state_encoder.feature_dim}, Action dim: {agent.rl_agent.action_encoder.MAX_ACTIONS}")
            logging.info(f"  Training mode: {training}")
            if model_path:
                logging.info(f"  Loaded model: {model_path}")
            return agent
        except Exception as e:
            logging.error(f"Failed to create Combat RL agent: {e}")
            logging.error("Falling back to OptimizedAgent")
            import traceback
            logging.debug(traceback.format_exc())
            return OptimizedAgent(chosen_class=player_class, elite_mode=elite_mode) if OPTIMIZED_AI_AVAILABLE else SimpleAgent(chosen_class=player_class, elite_mode=elite_mode)

    # Create RL agent
    if agent_type == "rl":
        _load_rl_components()
        if str(rl_version).lower() == "v2":
            rl_ready = RL_V2_AVAILABLE
        else:
            rl_ready = RL_AVAILABLE

        if not rl_ready:
            logging.error("RL agent requested but PyTorch/RL components not available")
            logging.error("Please install: pip install torch numpy")
            logging.error("Falling back to SimpleAgent")
            return SimpleAgent(chosen_class=player_class, elite_mode=elite_mode) if player_class else SimpleAgent(elite_mode=elite_mode)

        if player_class is None:
            logging.warning("RL agent requires player_class, defaulting to IRONCLAD")
            player_class = PlayerClass.IRONCLAD

        if player_class != PlayerClass.IRONCLAD:
            logging.warning(f"RL agent only supports IRONCLAD, got {player_class}")
            logging.warning("Falling back to SimpleAgent")
            return SimpleAgent(chosen_class=player_class, elite_mode=elite_mode)

        try:
            logging.info(f"Creating RL Agent (training={training})")

            # Auto-load latest checkpoint if in training mode and no model specified
            if training and model_path is None:
                auto_model_path = find_latest_checkpoint()
                if auto_model_path:
                    logging.info("Auto-loading latest checkpoint for continued training")
                    model_path = auto_model_path
                else:
                    logging.info("No existing checkpoints found, starting fresh training")

            agent = create_rl_agent(
                training=training,
                model_path=model_path,
                epsilon=epsilon,
                rl_version=rl_version,
                expert_mix_enabled=expert_mix_enabled,
                expert_mix_prob=expert_mix_prob,
                expert_warmup_steps=expert_warmup_steps,
                parent_policy_anchor_weight=parent_policy_anchor_weight,
                positive_energy_action_imitation_weight=(
                    positive_energy_action_imitation_weight
                ),
            )
            logging.info(f"RL Agent created successfully")
            logging.info(f"  State dim: {agent.state_encoder.feature_dim}, Action dim: {agent.action_encoder.MAX_ACTIONS}")
            logging.info(f"  Training mode: {training}")
            if model_path:
                logging.info(f"  Loaded model: {model_path}")
            return agent
        except Exception as e:
            logging.error(f"Failed to create RL agent: {e}")
            logging.error("Falling back to SimpleAgent")
            import traceback
            logging.debug(traceback.format_exc())
            return SimpleAgent(chosen_class=player_class, elite_mode=elite_mode)

    # Create OptimizedAgent
    if agent_type == "optimized":
        if not OPTIMIZED_AI_AVAILABLE:
            logging.warning("OptimizedAgent requested but components not available")
            logging.warning("Falling back to SimpleAgent")
            return SimpleAgent(chosen_class=player_class, elite_mode=elite_mode) if player_class else SimpleAgent(elite_mode=elite_mode)

        class_name = player_class.name if player_class else "Unknown"
        logging.info(f"Using OptimizedAgent with enhanced AI for {class_name}")
        return OptimizedAgent(chosen_class=player_class, elite_mode=elite_mode) if player_class else OptimizedAgent(elite_mode=elite_mode)

    # Create SimpleAgent (default)
    class_name = player_class.name if player_class else "Unknown"
    logging.info(f"Using SimpleAgent (legacy AI) for {class_name}")
    return SimpleAgent(chosen_class=player_class, elite_mode=elite_mode) if player_class else SimpleAgent(elite_mode=elite_mode)


def initialize_noncombat_exploration_if_configured(
    *,
    environ=None,
    repo_root=None,
    command=None,
    python_executable=None,
    training=False,
    agent_type="optimized",
    isolation_hashes=None,
):
    """Keep normal startup inert unless an explicit config path is present."""

    environment = os.environ if environ is None else environ
    raw_path = environment.get("STS_NONCOMBAT_EXPLORATION_CONFIG")
    if raw_path is None or not str(raw_path).strip():
        return None
    from spirecomm.ai.noncombat_exploration_runtime import (
        initialize_noncombat_exploration_runtime,
    )

    return initialize_noncombat_exploration_runtime(
        environ=environment,
        repo_root=Path(repo_root or Path(__file__).resolve().parent),
        command=list(command or sys.argv),
        python_executable=str(python_executable or sys.executable),
        training=bool(training),
        agent_type=str(agent_type),
        isolation_hashes=isolation_hashes,
    )


def initialize_card_uplift_shadow_if_configured(*, environ=None):
    """Keep card-uplift scoring or intervention inert without explicit config."""

    environment = os.environ if environ is None else environ
    raw_path = environment.get("STS_CARD_UPLIFT_SHADOW_CONFIG")
    canary_path = environment.get("STS_CARD_UPLIFT_CANARY_CONFIG")
    evaluation_path = environment.get("STS_CARD_UPLIFT_EVALUATION_CONFIG")
    shadow_configured = raw_path is not None and bool(str(raw_path).strip())
    canary_configured = canary_path is not None and bool(str(canary_path).strip())
    evaluation_configured = evaluation_path is not None and bool(
        str(evaluation_path).strip()
    )
    if sum((shadow_configured, canary_configured, evaluation_configured)) > 1:
        raise ValueError("card-uplift modes are mutually exclusive")
    if not any((shadow_configured, canary_configured, evaluation_configured)):
        return None
    from spirecomm.ai.card_uplift_shadow import (
        initialize_card_uplift_canary_runtime,
        initialize_card_uplift_evaluation_runtime,
        initialize_card_uplift_shadow_runtime,
    )

    if canary_configured:
        return initialize_card_uplift_canary_runtime(environ=environment)
    if evaluation_configured:
        return initialize_card_uplift_evaluation_runtime(environ=environment)
    return initialize_card_uplift_shadow_runtime(environ=environment)


def is_study_handshake_configured(environ=None):
    environment = os.environ if environ is None else environ
    from spirecomm.communication.study_handshake import HANDSHAKE_ATTEMPT_ENV

    return HANDSHAKE_ATTEMPT_ENV in environment


def initialize_study_handshake_if_configured(coordinator, *, environ=None):
    environment = os.environ if environ is None else environ
    from spirecomm.communication.study_handshake import (
        perform_child_handshake_if_configured,
    )

    return perform_child_handshake_if_configured(
        coordinator,
        environ=environment,
    )


def _qualification_require_no_follow_file(path_value):
    path = Path(path_value)
    path_components = path.parts[1:] if path.anchor else path.parts
    if any(":" in part for part in path_components):
        raise ValueError(
            "qualification handshake attempt path contains an alternate "
            "data stream"
        )
    if any(part.endswith((".", " ")) for part in path_components):
        raise ValueError(
            "qualification handshake attempt path contains a Win32 alias "
            "component"
        )
    lexical_path = Path(os.path.abspath(path_value))
    if not path.is_absolute() or str(lexical_path) != path_value:
        raise ValueError(
            "qualification handshake attempt path is not resolved absolute"
        )
    if lexical_path.drive.startswith("\\\\"):
        raise ValueError(
            "qualification handshake attempt path must use a local drive; "
            "UNC and device paths are forbidden"
        )
    current = Path(lexical_path.anchor)
    for part in lexical_path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError as exc:
            raise ValueError(
                f"qualification handshake attempt path is missing: {current}"
            ) from exc
        except OSError as exc:
            raise ValueError(
                "cannot inspect qualification handshake attempt path: "
                f"{current}: {exc}"
            ) from exc
        file_attributes = getattr(metadata, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if stat.S_ISLNK(metadata.st_mode) or bool(
            file_attributes & reparse_flag
        ):
            raise ValueError(
                "qualification handshake attempt path contains a symbolic "
                f"link or reparse point: {current}"
            )
    if not stat.S_ISREG(lexical_path.lstat().st_mode):
        raise ValueError(
            "qualification handshake attempt path is not a regular file"
        )
    return lexical_path


def _qualification_attempt_binding_if_requested(*, environ=None):
    environment = os.environ if environ is None else environ
    token = environment.get(QUALIFICATION_ATTEMPT_HASH_ENV)
    if token is None:
        return None
    from spirecomm.communication.study_handshake import (
        HANDSHAKE_ATTEMPT_ENV,
    )

    attempt_path = environment.get(HANDSHAKE_ATTEMPT_ENV)
    if attempt_path is None:
        raise ValueError("qualification exit requires a study handshake")
    if not isinstance(token, str) or re.fullmatch(r"[0-9a-f]{64}", token) is None:
        raise ValueError("qualification attempt-hash binding is invalid")
    if not isinstance(attempt_path, str) or not attempt_path.strip():
        raise ValueError("qualification handshake attempt path is invalid")
    guarded_attempt_path = _qualification_require_no_follow_file(attempt_path)
    return token, guarded_attempt_path


def qualification_exit_requested(*, environ=None):
    binding = _qualification_attempt_binding_if_requested(environ=environ)
    if binding is None:
        return False
    token, guarded_attempt_path = binding
    from spirecomm.communication.study_handshake import load_attempt_record

    attempt = load_attempt_record(guarded_attempt_path)
    if token != attempt["attempt_hash"]:
        raise ValueError("qualification attempt-hash binding mismatch")
    return True


def initialize_pre_agent_runtime(
    *,
    agent_type,
    environ=None,
    exploration_kwargs=None,
    exploration_initializer=None,
    coordinator_factory=None,
    handshake_initializer=None,
):
    """Preserve normal ordering while gating explicit study children first."""

    environment = os.environ if environ is None else environ
    exploration_initializer = (
        initialize_noncombat_exploration_if_configured
        if exploration_initializer is None
        else exploration_initializer
    )
    coordinator_factory = (
        create_ready_coordinator
        if coordinator_factory is None
        else coordinator_factory
    )
    handshake_initializer = (
        initialize_study_handshake_if_configured
        if handshake_initializer is None
        else handshake_initializer
    )
    exploration_arguments = dict(exploration_kwargs or {})
    if "environ" in exploration_arguments:
        raise ValueError("exploration_kwargs must not override environ")

    _qualification_attempt_binding_if_requested(environ=environment)
    handshake_configured = is_study_handshake_configured(environment)
    if handshake_configured:
        coordinator, input_thread_deferred = coordinator_factory(
            agent_type,
            force_input_thread=True,
        )
        handshake_completed = handshake_initializer(
            coordinator,
            environ=environment,
        )
        if handshake_completed and qualification_exit_requested(
            environ=environment,
        ):
            raise QualificationChildComplete
        exploration_runtime = exploration_initializer(
            environ=environment,
            **exploration_arguments,
        )
    else:
        exploration_runtime = exploration_initializer(
            environ=environment,
            **exploration_arguments,
        )
        coordinator, input_thread_deferred = coordinator_factory(
            agent_type,
            force_input_thread=False,
        )
    return coordinator, input_thread_deferred, exploration_runtime


if __name__ == "__main__":
    # Parse command line arguments
    agent_type = "auto"
    use_optimized = None  # Deprecated but kept for compatibility
    ascension_level = 0  # Default ascension level
    run_seed = None
    seed_pool = None
    seed_pool_path = None
    max_games = None
    training = False
    model_path = None
    epsilon = 0.0
    rl_version = None
    expert_mix_enabled = None
    expert_mix_prob = None
    expert_warmup_steps = None
    parent_policy_anchor_weight = None
    positive_energy_action_imitation_weight = None

    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Slay the Spire AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py                                  # Auto-detect, ascension 0, aggressive elites\n"
            "  python main.py --agent optimized                # Force optimized AI\n"
            "  python main.py --agent rl                       # Use RL agent (inference mode)\n"
            "  python main.py --agent rl --train               # Use RL agent in training mode\n"
            "  python main.py --agent combat_rl                # Combat-only RL with OptimizedAgent fallback\n"
            "  python main.py --agent combat_rl --train        # Train combat-only RL\n"
            "  python main.py --agent rl --model checkpoints/model.pth  # Load trained model\n"
            "  python main.py --agent combat_rl --rl-version v2 --eval --max-games 20\n"
            "  python main.py --agent rl --rl-version v2       # Use RL v2 action/observation space\n"
            "  python main.py --agent rl --rl-version v2 --train --expert-mix --expert-mix-prob 0.3 --expert-mix-warmup 5000\n"
            "  python main.py -a 10                            # Ascension level 10\n"
            "  python main.py -a 20                            # Ascension level 20\n"
            "  python main.py --agent optimized -a 20          # Optimized AI A20\n"
            "  python main.py --seed 7010470200064802279       # Fixed seed run\n"
            "  python main.py --seed-pool analysis_scripts/seed_pool.txt --max-games 20\n"
            "  python main.py --elite-route conservative -a 20 # Conservative elite routing (avoid elites)\n"
            "  python main.py --elite-route aggressive         # Aggressive elite routing (seek elites)\n"
            "  python main.py --elite-route adaptive           # Adaptive Ironclad elite routing\n"
        ),
    )
    parser.add_argument(
        "--agent",
        choices=["simple", "optimized", "rl", "combat_rl", "auto"],
        default="auto",
        help="Agent type: simple, optimized, rl, combat_rl, or auto-detect (default: auto)",
    )
    parser.add_argument(
        "--optimized",
        "-o",
        action="store_true",
        help="Use OptimizedAgent with enhanced AI (deprecated, use --agent optimized)",
    )
    parser.add_argument(
        "--simple",
        "-s",
        action="store_true",
        help="Use SimpleAgent (legacy AI) (deprecated, use --agent simple)",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Enable RL agent training mode (requires --agent rl)",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run RL agent in low-exploration evaluation mode; auto-loads latest checkpoint if --model is omitted",
    )
    parser.add_argument(
        "--model",
        metavar="PATH",
        help="Path to pre-trained RL model checkpoint (requires --agent rl)",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=None,
        metavar="P",
        help="RL inference exploration probability (0-1). Defaults to 0, or 0.05 with --eval.",
    )
    parser.add_argument(
        "--rl-version",
        choices=["v1", "v2"],
        default=None,
        help="RL space version for RL agents (default: STS_RL_VERSION or v1)",
    )
    parser.add_argument(
        "--expert-mix",
        action="store_true",
        help="Enable expert (OptimizedAgent) mixed exploration for RL v2 training",
    )
    parser.add_argument(
        "--expert-mix-prob",
        type=float,
        default=None,
        metavar="P",
        help="Expert action probability after warmup (0-1, default: env STS_RL_EXPERT_MIX_PROB or 0.3)",
    )
    parser.add_argument(
        "--expert-mix-warmup",
        type=int,
        default=None,
        metavar="N",
        help="Expert-only warmup steps before mixing (default: env STS_RL_EXPERT_WARMUP_STEPS or 5000)",
    )
    parser.add_argument(
        "--parent-policy-anchor-weight",
        type=float,
        default=None,
        metavar="W",
        help="Frozen parent-policy loss weight for RL v2 checkpoint continuation training",
    )
    parser.add_argument(
        "--positive-energy-action-imitation-weight",
        type=float,
        default=None,
        metavar="W",
        help=(
            "Executed-action imitation loss weight for positive-energy RL v2 "
            "training states"
        ),
    )
    parser.add_argument(
        "--ascension",
        "-a",
        default=None,
        metavar="N",
        help="Set ascension level (0-20, default: 0)",
    )
    parser.add_argument(
        "--seed",
        metavar="SEED",
        help="Set a fixed run seed (alphanumeric string)",
    )
    parser.add_argument(
        "--seed-pool",
        metavar="PATH",
        help="Path to seed pool file (one seed per line, # for comments)",
    )
    parser.add_argument(
        "--max-games",
        metavar="N",
        help="Stop after N games are completed (default: run forever)",
    )
    parser.add_argument(
        "--elite-route",
        choices=["conservative", "aggressive", "adaptive"],
        default="aggressive",
        help=(
            "Map routing (default: aggressive): conservative, aggressive, or "
            "adaptive. Adaptive requires a heuristic map owner and is "
            "unsupported for --agent rl."
        ),
    )
    parser.add_argument(
        "--noncombat-exploration-dry-run",
        action="store_true",
        help="Validate an explicit non-combat exploration session and exit before game startup.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["optimized", "simple"],
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    logging.info(
        "Startup: main=%s python=%s cwd=%s pid=%s",
        os.path.abspath(__file__),
        sys.executable,
        os.getcwd(),
        os.getpid(),
    )

    # Handle deprecated arguments
    if args.optimized and args.simple:
        logging.error("Cannot specify both --optimized and --simple")
        sys.exit(1)

    # Determine agent type from various arguments
    if args.mode == "optimized" or args.optimized:
        agent_type = "optimized"
        logging.info("Optimized AI mode enabled via command line")
    elif args.mode == "simple" or args.simple:
        agent_type = "simple"
        logging.info("Simple AI mode enforced via command line")
    elif args.agent != "auto":
        agent_type = args.agent
        logging.info(f"Agent type set to: {agent_type}")

    try:
        validate_agent_route_compatibility(agent_type, args.elite_route)
    except ValueError as error:
        parser.error(str(error))

    # RL-specific options
    if args.eval and args.train:
        logging.error("--eval and --train cannot be used together")
        sys.exit(1)

    if args.eval and agent_type not in ["rl", "combat_rl"]:
        logging.warning("--eval requires --agent rl or --agent combat_rl, ignoring")
        eval_mode = False
    else:
        eval_mode = args.eval

    if args.train and agent_type not in ["rl", "combat_rl"]:
        logging.warning("--train flag requires --agent rl or --agent combat_rl, ignoring")
        training = False
    else:
        training = args.train

    if args.model and agent_type not in ["rl", "combat_rl"]:
        logging.warning("--model flag requires --agent rl or --agent combat_rl, ignoring")
        model_path = None
    else:
        model_path = args.model

    if args.epsilon is not None:
        if not (0.0 <= args.epsilon <= 1.0):
            logging.error(f"--epsilon must be between 0 and 1, got {args.epsilon}")
            sys.exit(1)
        epsilon = args.epsilon
    elif eval_mode:
        epsilon = 0.05

    if eval_mode and model_path is None:
        auto_model_path = find_latest_checkpoint()
        if auto_model_path:
            model_path = auto_model_path
            logging.info("Evaluation mode auto-loading latest checkpoint: %s", model_path)
        else:
            logging.warning("Evaluation mode requested but no checkpoint was found")

    if args.rl_version is not None:
        rl_version = args.rl_version

    if args.expert_mix:
        expert_mix_enabled = True
    if args.expert_mix_prob is not None:
        expert_mix_prob = args.expert_mix_prob
        if expert_mix_enabled is None:
            expert_mix_enabled = True
    if args.expert_mix_warmup is not None:
        expert_warmup_steps = args.expert_mix_warmup
        if expert_mix_enabled is None:
            expert_mix_enabled = True

    if expert_mix_prob is not None and not (0.0 <= expert_mix_prob <= 1.0):
        logging.error(f"--expert-mix-prob must be between 0 and 1, got {expert_mix_prob}")
        sys.exit(1)
    if expert_warmup_steps is not None and expert_warmup_steps < 0:
        logging.error(f"--expert-mix-warmup must be >= 0, got {expert_warmup_steps}")
        sys.exit(1)

    if args.parent_policy_anchor_weight is not None:
        parent_policy_anchor_weight = args.parent_policy_anchor_weight
        if (
            not math.isfinite(parent_policy_anchor_weight)
            or parent_policy_anchor_weight < 0.0
        ):
            parser.error("--parent-policy-anchor-weight must be finite and non-negative")
        if parent_policy_anchor_weight > 0.0:
            if not training:
                parser.error("--parent-policy-anchor-weight requires --train")
            effective_rl_version = str(
                rl_version or os.environ.get("STS_RL_VERSION", "v1")
            ).lower()
            if effective_rl_version != "v2":
                parser.error("--parent-policy-anchor-weight requires --rl-version v2")
            if agent_type not in {"rl", "combat_rl"}:
                parser.error(
                    "--parent-policy-anchor-weight requires --agent rl or combat_rl"
                )

    if args.positive_energy_action_imitation_weight is not None:
        positive_energy_action_imitation_weight = (
            args.positive_energy_action_imitation_weight
        )
        if (
            not math.isfinite(positive_energy_action_imitation_weight)
            or positive_energy_action_imitation_weight < 0.0
        ):
            parser.error(
                "--positive-energy-action-imitation-weight must be finite and "
                "non-negative"
            )
        if positive_energy_action_imitation_weight > 0.0:
            if not training:
                parser.error(
                    "--positive-energy-action-imitation-weight requires --train"
                )
            effective_rl_version = str(
                rl_version or os.environ.get("STS_RL_VERSION", "v1")
            ).lower()
            if effective_rl_version != "v2":
                parser.error(
                    "--positive-energy-action-imitation-weight requires "
                    "--rl-version v2"
                )
            if agent_type not in {"rl", "combat_rl"}:
                parser.error(
                    "--positive-energy-action-imitation-weight requires --agent "
                    "rl or combat_rl"
                )

    if expert_mix_enabled and not training:
        logging.warning("Expert mix enabled but training is off; expert mix will be ignored.")

    if expert_mix_enabled and str(rl_version or os.environ.get("STS_RL_VERSION", "v1")).lower() != "v2":
        logging.warning("Expert mix only supported for RL v2; ignoring expert mix settings.")
        expert_mix_enabled = None
        expert_mix_prob = None
        expert_warmup_steps = None

    if training:
        logging.info("RL Agent training mode enabled")
        logging.info("  Models will be saved to: checkpoints/")
        backup_latest_checkpoint(
            os.path.join("checkpoints_archive", "combat_rl"),
            os.path.join("checkpoints", "rl_combat_model_ep*.pth"),
        )
        backup_latest_checkpoint(
            os.path.join("checkpoints_archive", "rl"),
            os.path.join("checkpoints", "rl_model_ep*.pth"),
        )
    elif eval_mode:
        logging.info("RL Agent evaluation mode enabled")
        logging.info("  Epsilon: %.3f", epsilon)

    if model_path:
        logging.info(f"Loading RL model from: {model_path}")

    if args.ascension is not None:
        try:
            ascension_level = int(args.ascension)
            if ascension_level < 0 or ascension_level > 20:
                logging.error(f"Ascension level must be 0-20, got {ascension_level}")
                sys.exit(1)
            logging.info(f"Ascension level set to {ascension_level}")
        except ValueError:
            logging.warning(f"Invalid ascension level: {args.ascension}")
            logging.warning("Ascension must be a number (0-20), ignoring and using default")

    if args.seed is not None:
        run_seed = str(args.seed).strip()
        if not run_seed:
            logging.error("Seed cannot be empty")
            sys.exit(1)
        logging.info(f"Run seed set to {run_seed}")

    if args.seed_pool is not None:
        seed_pool_path = str(args.seed_pool).strip()
        if not seed_pool_path:
            logging.error("Seed pool path cannot be empty")
            sys.exit(1)
        try:
            seed_pool = load_seed_pool(seed_pool_path)
        except Exception as e:
            logging.error(f"Failed to load seed pool: {e}")
            sys.exit(1)
        if not seed_pool:
            logging.error(f"Seed pool is empty: {seed_pool_path}")
            sys.exit(1)
        logging.info(f"Seed pool loaded: {len(seed_pool)} seeds from {seed_pool_path}")

    if args.max_games is not None:
        try:
            max_games = int(args.max_games)
            if max_games <= 0:
                raise ValueError("max-games must be positive")
            logging.info(f"Max games set to {max_games}")
        except ValueError:
            logging.error(f"Invalid --max-games value: {args.max_games}")
            sys.exit(1)

    if seed_pool and run_seed is not None:
        logging.warning("Both --seed and --seed-pool provided; ignoring --seed")
        run_seed = None

    elite_route_mode = args.elite_route
    logging.info(f"Elite route mode: {elite_route_mode}")

    handshake_configured = is_study_handshake_configured(os.environ)
    if (
        QUALIFICATION_ATTEMPT_HASH_ENV in os.environ
        and not handshake_configured
    ):
        try:
            qualification_exit_requested(environ=os.environ)
        except Exception as exc:
            logging.critical(
                "Qualification startup rejected: %s: %s",
                type(exc).__name__,
                exc,
            )
            sys.exit(2)
    exploration_kwargs = {
        "repo_root": Path(__file__).resolve().parent,
        "command": [
            sys.executable,
            str(Path(__file__).resolve()),
            *sys.argv[1:],
        ],
        "python_executable": sys.executable,
        "training": training,
        "agent_type": agent_type,
    }
    if args.noncombat_exploration_dry_run:
        if handshake_configured:
            logging.critical(
                "--noncombat-exploration-dry-run cannot use a study handshake"
            )
            sys.exit(2)
        try:
            exploration_runtime = initialize_noncombat_exploration_if_configured(
                environ=os.environ,
                **exploration_kwargs,
            )
        except Exception as exc:
            logging.critical(
                "Non-combat exploration startup rejected: %s: %s",
                type(exc).__name__,
                exc,
            )
            sys.exit(2)
        if exploration_runtime is None:
            logging.critical(
                "--noncombat-exploration-dry-run requires "
                "STS_NONCOMBAT_EXPLORATION_CONFIG"
            )
            sys.exit(2)
        logging.info("Non-combat exploration dry-run completed successfully")
        sys.exit(0)

    # Define player class before creating agent
    chosen_class = PlayerClass.IRONCLAD  # Fixed to Ironclad for testing

    try:
        coordinator, input_thread_deferred, exploration_runtime = (
            initialize_pre_agent_runtime(
                agent_type=agent_type,
                environ=os.environ,
                exploration_kwargs=exploration_kwargs,
            )
        )
    except QualificationChildComplete:
        logging.info(
            "Qualification child consumed release before exploration startup"
        )
        sys.exit(0)
    except Exception as exc:
        logging.critical(
            "Pre-agent runtime startup rejected: %s: %s",
            type(exc).__name__,
            exc,
        )
        sys.exit(2)

    # Create agent with player class and RL-specific options
    # This may take several seconds for RL agents (PyTorch, model loading)
    agent = create_agent(
        agent_type=agent_type,
        player_class=chosen_class,
        training=training,
        model_path=model_path,
        epsilon=epsilon,
        elite_mode=elite_route_mode,
        rl_version=rl_version,
        expert_mix_enabled=expert_mix_enabled,
        expert_mix_prob=expert_mix_prob,
        expert_warmup_steps=expert_warmup_steps,
        parent_policy_anchor_weight=parent_policy_anchor_weight,
        positive_energy_action_imitation_weight=(
            positive_energy_action_imitation_weight
        ),
    )

    try:
        card_uplift_shadow_runtime = initialize_card_uplift_shadow_if_configured(
            environ=os.environ
        )
    except Exception as exc:
        logging.critical(
            "Card-uplift runtime startup rejected: %s: %s",
            type(exc).__name__,
            exc,
        )
        sys.exit(2)

    # Register callbacks after agent is created
    coordinator.register_command_error_callback(agent.handle_error)
    state_change_callback = agent.get_next_action_in_game
    if exploration_runtime is not None:
        state_change_callback = exploration_runtime.wrap_state_callback(
            state_change_callback,
            policy_agent=agent,
        )
    if card_uplift_shadow_runtime is not None:
        state_change_callback = card_uplift_shadow_runtime.wrap_state_callback(
            state_change_callback
        )
    coordinator.register_state_change_callback(state_change_callback)
    coordinator.register_out_of_game_callback(agent.get_next_action_out_of_game)
    if input_thread_deferred:
        coordinator.start_input_thread()
        logging.info(
            "CommunicationMod stdin reader started after callback registration"
        )

    # Play games forever - IRONCLAD ONLY for testing
    game_count = 0

    # Set ascension level (default to 20 if not specified)
    current_ascension = ascension_level if ascension_level is not None else 20
    if not isinstance(current_ascension, int):
        current_ascension = 20  # Force to integer if 'auto' was passed

    while True:  # Infinite loop for Ironclad only
        game_count += 1
        is_rl_agent = (
            (RLAgent is not None and isinstance(agent, RLAgent))
            or (RLAgentV2 is not None and isinstance(agent, RLAgentV2))
        )
        is_combat_rl_agent = CombatRLAgent is not None and isinstance(agent, CombatRLAgent)
        active_seed = run_seed
        seed_pool_index = None
        if seed_pool:
            seed_pool_index = (game_count - 1) % len(seed_pool)
            active_seed = seed_pool[seed_pool_index]

        logging.info(f"\n{'='*60}\n")
        logging.info(f"Starting game #{game_count} as {chosen_class}")
        logging.info(f"Ascension Level: {current_ascension}")
        if active_seed is not None:
            logging.info(f"Seed: {active_seed}")
        if seed_pool_index is not None:
            logging.info(
                f"Seed pool: {seed_pool_index + 1}/{len(seed_pool)} ({seed_pool_path})"
            )
        logging.info(f"Coordinator state: in_game={coordinator.in_game}, ready={coordinator.game_is_ready}")
        if is_rl_agent:
            logging.info(
                f"RL Agent: training={training}, rl_version={rl_version or os.environ.get('STS_RL_VERSION', 'v1')}"
            )
        if is_combat_rl_agent:
            logging.info(f"Combat RL Agent: training={training}")
        logging.info(f"{'='*60}\n")

        # Reset game tracker for OptimizedAgent and CombatRLAgent's fallback
        try:
            from spirecomm.ai.tracker import GameTracker

            if isinstance(agent, OptimizedAgent) and hasattr(agent, 'game_tracker'):
                agent.game_tracker = GameTracker()
                agent.game_tracker.player_class = str(chosen_class).replace('PlayerClass.', '')
                agent.game_tracker.ascension_level = current_ascension
                # Reset tracking state flags
                agent._in_combat = False
                agent._last_relics = set()
            elif is_combat_rl_agent and hasattr(agent, 'fallback_agent'):
                fallback = agent.fallback_agent
                if isinstance(fallback, OptimizedAgent) and hasattr(fallback, 'game_tracker'):
                    fallback.game_tracker = GameTracker()
                    fallback.game_tracker.player_class = str(chosen_class).replace('PlayerClass.', '')
                    fallback.game_tracker.ascension_level = current_ascension
                    # Reset tracking state flags
                    fallback._in_combat = False
                    fallback._last_relics = set()
        except Exception as e:
            logging.warning(f"Could not reset game tracker: {e}")

        # Change agent class for this game (only for non-RL agents)
        if not is_rl_agent and not is_combat_rl_agent and hasattr(agent, 'change_class'):
            agent.change_class(chosen_class)
        elif is_rl_agent or is_combat_rl_agent:
            # RL agent doesn't need change_class, just reset
            agent.reset()

        if exploration_runtime is not None:
            try:
                exploration_runtime.begin_game(
                    f"game-{game_count}:seed-{active_seed or 'random'}"
                )
            except Exception as exc:
                logging.critical(
                    "Could not begin non-combat exploration trajectory: %s",
                    exc,
                )
                break

        # Play the game
        game_completed = False
        try:
            result = coordinator.play_one_game(
                chosen_class,
                ascension_level=current_ascension,
                seed=active_seed,
            )
            game_completed = True
        except EOFError as e:
            # Handle broken pipe (Communication Mod or game crashed)
            import traceback
            logging.critical(f"Game #{game_count} CRASHED: {e}")
            logging.critical("This indicates Communication Mod or Slay the Spire terminated unexpectedly.")
            logging.critical("Possible causes:")
            logging.critical("  1. SuperFastMode mod conflict (try disabling it)")
            logging.critical("  2. Communication Mod crash (check mod version)")
            logging.critical("  3. Slay the Spire crash (check game logs)")
            logging.critical("Action: Waiting 10 seconds before attempting to continue...")
            logging.debug(traceback.format_exc())

            # Wait for user to notice and potentially restart the game
            import time
            time.sleep(10)

            # Exit the program because communication threads are dead and cannot be easily restarted
            # User will need to restart the game and then the AI
            logging.critical("Exiting... Please restart Slay the Spire and then run the AI again.")
            sys.exit(1)
        except Exception as e:
            # Handle communication errors or game crashes
            import traceback
            logging.error(f"Game #{game_count} failed: {e}\n" + "".join(traceback.format_exc()))

            if is_unrecoverable_run_error(e):
                logging.critical(
                    "Stopping batch after unrecoverable Communication Mod/game-state error. "
                    "Restart Slay the Spire before launching another run."
                )
                break

            # Try to restart Communication Mod connection by waiting a bit
            import time
            time.sleep(2)  # Wait for Communication Mod to recover

            # Continue to next game instead of crashing
            continue
        finally:
            if exploration_runtime is not None:
                terminal_state = (
                    getattr(coordinator, "game_over_state", None)
                    or getattr(coordinator, "last_game_state", None)
                )
                try:
                    exploration_runtime.end_game(terminal_state)
                except Exception as exc:
                    logging.error(
                        "Could not finalize non-combat exploration trajectory: %s",
                        exc,
                    )
            if training and (is_rl_agent or is_combat_rl_agent):
                try:
                    if game_completed:
                        finalize_training_episode = getattr(
                            agent,
                            "finalize_training_episode",
                            None,
                        )
                        if callable(finalize_training_episode):
                            terminal_state = (
                                getattr(coordinator, "game_over_state", None)
                                or getattr(coordinator, "last_game_state", None)
                            )
                            if terminal_state is not None:
                                finalize_training_episode(terminal_state)
                            else:
                                abort_training_episode = getattr(
                                    agent,
                                    "abort_training_episode",
                                    None,
                                )
                                if callable(abort_training_episode):
                                    abort_training_episode()
                    else:
                        abort_training_episode = getattr(
                            agent,
                            "abort_training_episode",
                            None,
                        )
                        if callable(abort_training_episode):
                            abort_training_episode()
                except Exception as exc:
                    logging.error("Could not close RL training episode: %s", exc)

        # Record game result if statistics available or RL agent in training
        if is_rl_agent and training:
            # RL agent training checkpoint saving
            try:
                # Create checkpoints directory if it doesn't exist
                os.makedirs("checkpoints", exist_ok=True)

                # Save checkpoint
                suffix = get_training_checkpoint_suffix(agent, game_count)
                checkpoint_path = f"checkpoints/rl_model_{suffix}.pth"
                agent.save_model(checkpoint_path, episode=game_count)

                logging.info(f"RL Training checkpoint saved: {checkpoint_path}")

                # Log training metrics
                if hasattr(agent, 'trainer') and agent.trainer:
                    avg_loss = agent.trainer.get_avg_loss()
                    epsilon = agent.trainer.get_epsilon()
                    total_steps = agent.trainer.total_steps
                    logging.info(f"  Training steps: {total_steps}")
                    logging.info(f"  Avg loss: {avg_loss:.4f}")
                    logging.info(f"  Epsilon: {epsilon:.3f}")

                # Reset agent for next episode
                agent.reset()
            except Exception as e:
                logging.error(f"Error saving RL checkpoint: {e}")
                import traceback
                logging.debug(traceback.format_exc())

        # Combat RL agent training checkpoint saving
        if is_combat_rl_agent and training:
            # Combat RL agent training checkpoint saving
            try:
                # Create checkpoints directory if it doesn't exist
                os.makedirs("checkpoints", exist_ok=True)

                # Save checkpoint with combat_rl naming
                suffix = get_training_checkpoint_suffix(agent, game_count)
                checkpoint_path = f"checkpoints/rl_combat_model_{suffix}.pth"
                agent.save_model(checkpoint_path, episode=game_count)

                logging.info(f"Combat RL Training checkpoint saved: {checkpoint_path}")

                # Clean up old checkpoints, keep only the most recent N
                MAX_CHECKPOINTS = 5
                checkpoint_files = sorted(
                    glob.glob("checkpoints/rl_combat_model_ep*.pth"),
                    key=os.path.getmtime
                )
                if len(checkpoint_files) > MAX_CHECKPOINTS:
                    for old_checkpoint in checkpoint_files[:-MAX_CHECKPOINTS]:
                        os.remove(old_checkpoint)
                        logging.info(f"Removed old checkpoint: {old_checkpoint}")

                # Log training metrics
                if hasattr(agent, 'rl_agent') and hasattr(agent.rl_agent, 'trainer') and agent.rl_agent.trainer:
                    avg_loss = agent.rl_agent.trainer.get_avg_loss()
                    epsilon = agent.rl_agent.trainer.get_epsilon()
                    total_steps = agent.rl_agent.trainer.total_steps
                    logging.info(f"  Training steps: {total_steps}")
                    logging.info(f"  Avg loss: {avg_loss:.4f}")
                    logging.info(f"  Epsilon: {epsilon:.3f}")

                # Reset agent for next episode
                agent.reset()
            except Exception as e:
                logging.error(f"Error saving Combat RL checkpoint: {e}")
                import traceback
                logging.debug(traceback.format_exc())

        # Mark AI games (always do this, independent of statistics)
        try:
            # Use current timestamp to mark AI game
            import time

            game_timestamp = int(time.time())
            logging.info(f"  Game timestamp: {game_timestamp}")

            # Mark this game as AI-played (relative path, runs from game directory)
            ai_games_file = Path("runs/ai_games.txt")
            ai_games_file.parent.mkdir(parents=True, exist_ok=True)
            with open(ai_games_file, 'a') as f:
                f.write(f"{game_timestamp}\n")
            logging.debug(f"  Marked as AI game in runs/ai_games.txt")
        except Exception:
            pass

        # Periodic run archiving during training
        if training and (is_rl_agent or is_combat_rl_agent) and game_count % 200 == 0:
            character_dir = chosen_class.name if hasattr(chosen_class, "name") else str(chosen_class)
            archived, kept = archive_old_runs(character_dir, keep=1000)
            logging.info(
                f"Run archive maintenance: archived={archived} kept={kept} character={character_dir}"
            )

        # Print summary if OptimizedAgent or CombatRLAgent (to stderr)
        if isinstance(agent, OptimizedAgent):
            try:
                summary = agent.get_decision_summary()
                log_decision_summary(summary)

                # Print deck stats if available
                deck_stats = agent.get_deck_stats()
                if 'error' not in deck_stats:
                    logging.info(f"\nDeck Statistics:\n")
                    logging.info(f"  Size: {deck_stats['size']}\n")
                    logging.info(f"  Archetype: {deck_stats['archetype']}\n")
                    logging.info(f"  Quality: {deck_stats['quality']:.2f}\n")
                    logging.info(f"  Upgrade Rate: {deck_stats.get('upgrade_rate', 0):.2%}\n")
            except Exception as e:
                logging.info(f"Error generating summary: {e}\n")
        elif is_combat_rl_agent and hasattr(agent, 'fallback_agent') and isinstance(agent.fallback_agent, OptimizedAgent):
            try:
                summary = agent.fallback_agent.get_decision_summary()
                log_decision_summary(summary, "Game Summary (OptimizedAgent fallback)")

                # Print deck stats if available
                deck_stats = agent.fallback_agent.get_deck_stats()
                if 'error' not in deck_stats:
                    logging.info(f"\nDeck Statistics:\n")
                    logging.info(f"  Size: {deck_stats['size']}\n")
                    logging.info(f"  Archetype: {deck_stats['archetype']}\n")
                    logging.info(f"  Quality: {deck_stats['quality']:.2f}\n")
                    logging.info(f"  Upgrade Rate: {deck_stats.get('upgrade_rate', 0):.2%}\n")
            except Exception as e:
                logging.info(f"Error generating summary: {e}\n")

        if max_games is not None and game_count >= max_games:
            logging.info(f"Max games reached ({max_games}); exiting.")
            break
