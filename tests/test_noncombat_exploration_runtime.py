import builtins
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from spirecomm.ai.noncombat_exploration import (
    CONFIG_ENV,
    CONFIG_SCHEMA_VERSION,
    ExplorationDecisionResult,
    ExplorationConfigurationError,
    ExplorationPersistenceError,
)
from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai import noncombat_exploration_runtime as runtime_module
from spirecomm.ai.noncombat_exploration_runtime import (
    GitSourceState,
    initialize_noncombat_exploration_runtime,
)
from spirecomm.ai.tracker import GameTracker
from spirecomm.communication.action import (
    BuyCardAction,
    CancelAction,
    CardRewardAction,
    EventOptionAction,
    LeaveAction,
)
from spirecomm.spire.screen import ScreenType


SOURCE_COMMIT = "c" * 40


def test_properties_fingerprint_has_comment_and_order_stable_semantic_hash(
    tmp_path,
):
    config_path = tmp_path / "config.properties"
    config_path.write_text(
        "#Tue Jul 14 01:00:00 CST 2026\nverbose=false\nrunAtGameStart=true\n",
        encoding="utf-8",
    )
    before = runtime_module._file_fingerprint(config_path)
    config_path.write_text(
        "#Tue Jul 14 01:10:00 CST 2026\nrunAtGameStart=true\nverbose=false\n",
        encoding="utf-8",
    )
    after = runtime_module._file_fingerprint(config_path)

    assert before["sha256"] != after["sha256"]
    assert before["semantic_sha256"] == after["semantic_sha256"]


def test_properties_semantic_hash_respects_last_duplicate_value(tmp_path):
    config_path = tmp_path / "config.properties"
    config_path.write_text(
        "command=first\ncommand=second\nverbose=false\n",
        encoding="iso-8859-1",
    )
    first = runtime_module._file_fingerprint(config_path)
    config_path.write_text(
        "command=second\ncommand=first\nverbose=false\n",
        encoding="iso-8859-1",
    )
    second = runtime_module._file_fingerprint(config_path)

    assert first["semantic_sha256"] != second["semantic_sha256"]


def test_properties_semantic_hash_decodes_java_escapes_and_continuations(
    tmp_path,
):
    config_path = tmp_path / "config.properties"
    config_path.write_text(
        "co\\u006dmand=python \\\n"
        "  main.py\n"
        "verbose:false\n",
        encoding="iso-8859-1",
    )
    escaped = runtime_module._file_fingerprint(config_path)
    config_path.write_text(
        "verbose = false\ncommand = python main.py\n",
        encoding="iso-8859-1",
    )
    plain = runtime_module._file_fingerprint(config_path)

    assert escaped["semantic_sha256"] == plain["semantic_sha256"]


@pytest.mark.parametrize("embedded", ["\f", "\v", "\x85"])
def test_properties_semantic_hash_preserves_non_crlf_control_characters(
    tmp_path,
    embedded,
):
    config_path = tmp_path / "config.properties"
    config_path.write_text(
        f"command=foo{embedded}bar=baz\n",
        encoding="iso-8859-1",
    )
    one_property = runtime_module._file_fingerprint(config_path)
    config_path.write_text(
        "command=foo\nbar=baz\n",
        encoding="iso-8859-1",
    )
    two_properties = runtime_module._file_fingerprint(config_path)

    assert one_property["semantic_sha256"] != two_properties["semantic_sha256"]


def _write_config(tmp_path, *, rates=None, budget=2, source_commit=SOURCE_COMMIT):
    config_path = tmp_path / "exploration.json"
    payload = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "session_id": "runtime-session",
        "seed": 17,
        "enabled_categories": ["card_reward", "shop"],
        "category_rates_bps": rates or {"card_reward": 500, "shop": 500},
        "per_run_alternative_budget": budget,
        "trace_path": str((tmp_path / "trace.jsonl").resolve()),
        "manifest_path": str((tmp_path / "manifest.json").resolve()),
        "source_commit": source_commit,
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    return config_path, payload


def _clean_source(_repo_root):
    return GitSourceState(
        commit=SOURCE_COMMIT,
        tracked_clean=True,
        tracked_status="",
    )


def _initialize(tmp_path, monkeypatch, *, rates=None, training=False):
    config_path, payload = _write_config(tmp_path, rates=rates)
    monkeypatch.setattr(runtime_module, "inspect_git_source", _clean_source)
    runtime = initialize_noncombat_exploration_runtime(
        environ={CONFIG_ENV: str(config_path)},
        repo_root=tmp_path,
        command=[sys.executable, "main.py", "--agent", "optimized"],
        python_executable=sys.executable,
        training=training,
        agent_type="optimized",
        isolation_hashes={"communication_mod_config": {"exists": False}},
    )
    return runtime, payload


def _reward_game(card):
    return SimpleNamespace(
        screen_type=ScreenType.CARD_REWARD,
        screen=SimpleNamespace(cards=[card], can_skip=True, can_bowl=False),
        available_commands=["choose", "cancel", "state"],
        cancel_available=True,
        proceed_available=False,
        choice_available=True,
        in_combat=False,
        floor=3,
        act=1,
        room_type="MonsterRoom",
        gold=99,
        current_hp=70,
        max_hp=80,
        deck=[],
        relics=[],
        potions=[],
        hand=[],
        monsters=[],
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=3),
    )


def _shop_game(card):
    game = _reward_game(card)
    game.screen_type = ScreenType.SHOP_SCREEN
    game.screen = SimpleNamespace(
        cards=[card],
        relics=[],
        potions=[],
        purge_available=False,
        purge_cost=75,
    )
    game.available_commands = ["choose", "leave", "state"]
    game.cancel_available = True
    return game


def _stateful_policy_agent(game):
    agent = SimpleAgent.__new__(SimpleAgent)
    agent.game = game
    agent.skipped_cards = False
    agent.visited_shop = True
    agent.shop_purchase_made = False
    agent._shop_purchase_signature = None
    agent._shop_bought_card_this_shop = False
    agent._shop_purged_this_shop = False
    agent._leaving_shop_room = False
    agent._shop_exit_waits = 0
    agent.decision_history = []
    agent.game_tracker = GameTracker()
    return agent


def _force_selection(monkeypatch, runtime, *, alternative):
    def consider(adapter, _game):
        selected_action_id = (
            adapter.proposal.alternative_action_id
            if alternative
            else adapter.proposal.baseline_action_id
        )
        action = adapter.materialize_or_current(selected_action_id)
        return ExplorationDecisionResult(
            action=action,
            known_propensity=True,
            decision_id="forced-decision",
            selected_action_id=selected_action_id,
            selection=SimpleNamespace(
                selected_probability_numerator=1000 if alternative else 9000,
                selected_probability_denominator=10000,
            ),
        )

    monkeypatch.setattr(runtime.controller, "consider", consider)


def test_absent_config_is_inert_and_does_not_inspect_git_or_create_artifacts(
    tmp_path, monkeypatch
):
    def fail_if_called(_repo_root):
        raise AssertionError("git inspection should be skipped")

    monkeypatch.setattr(runtime_module, "inspect_git_source", fail_if_called)

    runtime = initialize_noncombat_exploration_runtime(
        environ={},
        repo_root=tmp_path,
        command=[sys.executable, "main.py"],
        python_executable=sys.executable,
        training=False,
        agent_type="optimized",
    )

    assert runtime is None
    assert list(tmp_path.iterdir()) == []


def test_absent_config_leaves_reward_and_shop_callbacks_exactly_unwrapped(tmp_path):
    runtime = initialize_noncombat_exploration_runtime(
        environ={},
        repo_root=tmp_path,
        command=[sys.executable, "main.py"],
        python_executable=sys.executable,
        training=False,
        agent_type="optimized",
    )
    reward_card = SimpleNamespace(name="Anger", card_id="Anger", price=0, upgrades=0)
    shop_card = SimpleNamespace(
        name="Perfected Strike",
        card_id="Perfected Strike",
        price=50,
        upgrades=0,
    )
    cases = [
        (_reward_game(reward_card), CardRewardAction(reward_card)),
        (_shop_game(shop_card), BuyCardAction(shop_card)),
    ]

    for game, current in cases:
        current_callback = lambda _game, action=current: action
        active_callback = (
            runtime.wrap_state_callback(current_callback)
            if runtime is not None
            else current_callback
        )
        assert active_callback(game) is current


def test_invalid_config_fails_before_manifest_creation(tmp_path, monkeypatch):
    config_path, payload = _write_config(tmp_path)
    payload["category_rates_bps"]["shop"] = 1001
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(runtime_module, "inspect_git_source", _clean_source)

    with pytest.raises(ExplorationConfigurationError, match="1,000"):
        initialize_noncombat_exploration_runtime(
            environ={CONFIG_ENV: str(config_path)},
            repo_root=tmp_path,
            command=[sys.executable, "main.py"],
            python_executable=sys.executable,
            training=False,
            agent_type="optimized",
            isolation_hashes={},
        )

    assert not Path(payload["manifest_path"]).exists()
    assert not Path(payload["trace_path"]).exists()


def test_tracked_dirty_source_refuses_startup_without_session_artifact(
    tmp_path, monkeypatch
):
    config_path, payload = _write_config(tmp_path)
    monkeypatch.setattr(
        runtime_module,
        "inspect_git_source",
        lambda _root: GitSourceState(
            commit=SOURCE_COMMIT,
            tracked_clean=False,
            tracked_status=" M main.py",
        ),
    )

    with pytest.raises(ExplorationPersistenceError, match="tracked source is dirty"):
        initialize_noncombat_exploration_runtime(
            environ={CONFIG_ENV: str(config_path)},
            repo_root=tmp_path,
            command=[sys.executable, "main.py"],
            python_executable=sys.executable,
            training=False,
            agent_type="optimized",
            isolation_hashes={},
        )

    assert not Path(payload["manifest_path"]).exists()


def test_source_commit_mismatch_refuses_startup(tmp_path, monkeypatch):
    config_path, payload = _write_config(tmp_path)
    monkeypatch.setattr(
        runtime_module,
        "inspect_git_source",
        lambda _root: GitSourceState(
            commit="d" * 40,
            tracked_clean=True,
            tracked_status="",
        ),
    )

    with pytest.raises(ExplorationPersistenceError, match="source commit mismatch"):
        initialize_noncombat_exploration_runtime(
            environ={CONFIG_ENV: str(config_path)},
            repo_root=tmp_path,
            command=[sys.executable, "main.py"],
            python_executable=sys.executable,
            training=False,
            agent_type="optimized",
            isolation_hashes={},
        )

    assert not Path(payload["manifest_path"]).exists()


def test_valid_config_creates_manifest_but_not_trace(tmp_path, monkeypatch):
    runtime, payload = _initialize(tmp_path, monkeypatch)

    assert runtime is not None
    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["session_id"] == "runtime-session"
    assert manifest["source"]["commit"] == SOURCE_COMMIT
    assert manifest["source"]["tracked_clean"] is True
    assert not Path(payload["trace_path"]).exists()


def test_training_mode_is_rejected_before_manifest_creation(tmp_path, monkeypatch):
    config_path, payload = _write_config(tmp_path)
    monkeypatch.setattr(runtime_module, "inspect_git_source", _clean_source)

    with pytest.raises(ExplorationConfigurationError, match="no-training"):
        initialize_noncombat_exploration_runtime(
            environ={CONFIG_ENV: str(config_path)},
            repo_root=tmp_path,
            command=[sys.executable, "main.py", "--train"],
            python_executable=sys.executable,
            training=True,
            agent_type="combat_rl",
            isolation_hashes={},
        )

    assert not Path(payload["manifest_path"]).exists()


def test_zero_rate_wrapper_returns_exact_current_action_and_writes_no_trace(
    tmp_path, monkeypatch
):
    runtime, payload = _initialize(
        tmp_path,
        monkeypatch,
        rates={"card_reward": 0, "shop": 0},
    )
    card = SimpleNamespace(name="Anger", card_id="Anger", price=0, upgrades=0)
    game = _reward_game(card)
    current = CardRewardAction(card)
    callback_calls = []

    def current_policy(observed_game):
        callback_calls.append(observed_game)
        return current

    runtime.begin_game("run-1")
    wrapped = runtime.wrap_state_callback(current_policy)
    action = wrapped(game)

    assert action is current
    assert callback_calls == [game]
    assert not Path(payload["trace_path"]).exists()


def test_zero_rate_shop_wrapper_preserves_current_action_and_shop_state(
    tmp_path, monkeypatch
):
    runtime, payload = _initialize(
        tmp_path,
        monkeypatch,
        rates={"card_reward": 0, "shop": 0},
    )
    card = SimpleNamespace(
        name="Perfected Strike",
        card_id="Perfected Strike",
        price=50,
        upgrades=0,
    )
    game = _shop_game(card)
    current = BuyCardAction(card)
    policy_agent = SimpleNamespace(
        game=game,
        visited_shop=True,
        shop_purchase_made=True,
        _shop_purchase_signature=(150, False, 1, 0, 0),
        _shop_bought_card_this_shop=True,
        _shop_purged_this_shop=False,
        _leaving_shop_room=False,
        _shop_exit_waits=0,
    )
    before = dict(vars(policy_agent))
    runtime.begin_game("run-1")

    action = runtime.wrap_state_callback(
        lambda _game: current,
        policy_agent=policy_agent,
    )(game)

    assert action is current
    assert vars(policy_agent) == before
    assert not Path(payload["trace_path"]).exists()


def test_alternative_card_skip_rolls_back_baseline_bookkeeping_and_commits_skip(
    tmp_path,
    monkeypatch,
):
    runtime, _payload = _initialize(
        tmp_path,
        monkeypatch,
        rates={"card_reward": 1000, "shop": 1000},
    )
    card = SimpleNamespace(name="Anger", card_id="Anger", price=0, upgrades=0)
    game = _reward_game(card)
    current = CardRewardAction(card)
    policy_agent = _stateful_policy_agent(game)
    runtime.begin_game("run-1")
    _force_selection(monkeypatch, runtime, alternative=True)

    def current_policy(_game):
        policy_agent.game_tracker.record_card_choice(
            chosen="Anger",
            skipped=0,
            available=["Anger"],
        )
        policy_agent.game_tracker.record_decision(
            decision_type="reward",
            confidence=0.8,
        )
        policy_agent.decision_history.append(
            {"type": "card_reward", "card": "Anger"}
        )
        return current

    action = runtime.wrap_state_callback(
        current_policy,
        policy_agent=policy_agent,
    )(game)

    assert isinstance(action, CancelAction)
    assert policy_agent.skipped_cards is True
    assert policy_agent.game_tracker.cards_obtained == []
    assert policy_agent.game_tracker.cards_skipped == 1
    assert policy_agent.game_tracker.total_decisions == 0
    assert policy_agent.decision_history == []


def test_alternative_shop_leave_rolls_back_purchase_and_commits_exit_state(
    tmp_path,
    monkeypatch,
):
    runtime, _payload = _initialize(
        tmp_path,
        monkeypatch,
        rates={"card_reward": 1000, "shop": 1000},
    )
    card = SimpleNamespace(
        name="Perfected Strike",
        card_id="Perfected Strike",
        price=50,
        upgrades=0,
    )
    game = _shop_game(card)
    current = BuyCardAction(card)
    policy_agent = _stateful_policy_agent(game)
    runtime.begin_game("run-1")
    _force_selection(monkeypatch, runtime, alternative=True)

    def current_policy(_game):
        policy_agent._mark_shop_purchase(99, game.screen, bought_card=True)
        return current

    action = runtime.wrap_state_callback(
        current_policy,
        policy_agent=policy_agent,
    )(game)

    assert isinstance(action, LeaveAction)
    assert policy_agent.shop_purchase_made is False
    assert policy_agent._shop_purchase_signature is None
    assert policy_agent._shop_bought_card_this_shop is False
    assert policy_agent._leaving_shop_room is True
    assert policy_agent._shop_exit_waits == 0


def test_baseline_arm_commits_original_policy_bookkeeping(
    tmp_path,
    monkeypatch,
):
    runtime, _payload = _initialize(
        tmp_path,
        monkeypatch,
        rates={"card_reward": 1000, "shop": 1000},
    )
    card = SimpleNamespace(name="Anger", card_id="Anger", price=0, upgrades=0)
    game = _reward_game(card)
    current = CardRewardAction(card)
    policy_agent = _stateful_policy_agent(game)
    runtime.begin_game("run-1")
    _force_selection(monkeypatch, runtime, alternative=False)

    def current_policy(_game):
        policy_agent.game_tracker.record_card_choice(
            chosen="Anger",
            skipped=0,
            available=["Anger"],
        )
        policy_agent.game_tracker.record_decision(
            decision_type="reward",
            confidence=0.8,
        )
        policy_agent.decision_history.append(
            {"type": "card_reward", "card": "Anger"}
        )
        return current

    action = runtime.wrap_state_callback(
        current_policy,
        policy_agent=policy_agent,
    )(game)

    assert action is current
    assert policy_agent.skipped_cards is False
    assert policy_agent.game_tracker.cards_obtained == ["Anger"]
    assert policy_agent.game_tracker.cards_skipped == 0
    assert policy_agent.game_tracker.total_decisions == 1
    assert policy_agent.decision_history == [
        {"type": "card_reward", "card": "Anger"}
    ]


def test_event_shadow_observation_never_replaces_current_action(tmp_path, monkeypatch):
    runtime, payload = _initialize(tmp_path, monkeypatch)
    options = [
        SimpleNamespace(text="Pray", label="Pray", disabled=False, choice_index=0),
        SimpleNamespace(text="Leave", label="Leave", disabled=False, choice_index=1),
    ]
    game = SimpleNamespace(
        **vars(_reward_game(SimpleNamespace(name="Anger", card_id="Anger")))
    )
    game.screen_type = ScreenType.EVENT
    game.screen = SimpleNamespace(
        event_name="Golden Shrine",
        event_id="GoldenShrine",
        options=options,
    )
    game.available_commands = ["choose", "state"]
    current = EventOptionAction(options[0])
    runtime.begin_game("run-1")

    action = runtime.wrap_state_callback(lambda _game: current)(game)

    assert action is current
    assert not Path(payload["trace_path"]).exists()


def test_adapter_construction_failure_fails_closed_to_current_action(
    tmp_path, monkeypatch
):
    runtime, payload = _initialize(tmp_path, monkeypatch)
    card = SimpleNamespace(name="Anger", card_id="Anger", price=0, upgrades=0)
    game = _reward_game(card)
    current = CardRewardAction(card)
    runtime.begin_game("run-1")

    def broken_adapter(*_args, **_kwargs):
        raise ValueError("non-json game field")

    monkeypatch.setattr(runtime_module, "_build_adapter", broken_adapter)

    action = runtime.wrap_state_callback(lambda _game: current)(game)

    assert action is current
    assert not Path(payload["trace_path"]).exists()


def test_each_game_gets_a_fresh_trajectory_controller_state(tmp_path, monkeypatch):
    runtime, _payload = _initialize(tmp_path, monkeypatch)

    first = runtime.begin_game("run-1")
    runtime.end_game()
    second = runtime.begin_game("run-2")

    assert first != second
    assert runtime.controller.trajectory_session_id == second
    assert runtime.controller.alternative_attempts == 0


def test_runtime_initialization_does_not_import_rl_or_modify_checkpoint(
    tmp_path, monkeypatch
):
    checkpoint = tmp_path / "checkpoints" / "rl_combat_model_ep1.pth"
    checkpoint.parent.mkdir()
    checkpoint.write_bytes(b"checkpoint-sentinel")
    before_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    before_stat = checkpoint.stat()
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "torch" or name.startswith("spirecomm.ai.rl"):
            raise AssertionError(f"runtime attempted to import {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    _initialize(tmp_path, monkeypatch, rates={"card_reward": 0, "shop": 0})

    after_stat = checkpoint.stat()
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == before_hash
    assert after_stat.st_size == before_stat.st_size
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
