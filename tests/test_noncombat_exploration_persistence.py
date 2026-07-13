import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from spirecomm.ai.noncombat_exploration import (
    CONFIG_SCHEMA_VERSION,
    ExplorationConfig,
    ExplorationPersistenceError,
    ExplorationRecordStore,
    NonCombatExplorationController,
    build_card_reward_proposal,
    build_shop_proposal,
    confirmed_exploration_decisions,
    create_exploration_session_manifest,
    make_decision_id,
    make_trajectory_session_id,
    sample_exploration,
)
from spirecomm.communication.action import (
    BuyCardAction,
    CancelAction,
    CardRewardAction,
    ChooseAction,
    LeaveAction,
)
from spirecomm.spire.screen import ScreenType


SOURCE_COMMIT = "a" * 40


def _item(name, *, price=0):
    return SimpleNamespace(
        name=name,
        card_id=name,
        relic_id=name,
        potion_id=name,
        price=price,
        upgrades=0,
    )


def _game(screen_type, screen, *, commands, gold=150, deck=None):
    return SimpleNamespace(
        screen_type=screen_type,
        screen=screen,
        available_commands=list(commands),
        cancel_available=any(
            command in commands for command in ("cancel", "leave", "return", "skip")
        ),
        proceed_available=any(command in commands for command in ("proceed", "confirm")),
        in_combat=False,
        floor=7,
        act=1,
        room_type="MonsterRoom",
        gold=gold,
        current_hp=62,
        max_hp=80,
        deck=list(deck or [_item("Strike_R")]),
        relics=[],
        potions=[],
        hand=[],
        monsters=[],
        player=SimpleNamespace(current_hp=62, max_hp=80, block=0, energy=3),
    )


def _reward_game(*, cards=None, deck=None):
    return _game(
        ScreenType.CARD_REWARD,
        SimpleNamespace(
            cards=list(cards or [_item("Anger")]),
            can_skip=True,
            can_bowl=False,
        ),
        commands=["choose", "cancel", "state"],
        deck=deck,
    )


def _shop_game(*, cards=None, purge_available=False, gold=150):
    return _game(
        ScreenType.SHOP_SCREEN,
        SimpleNamespace(
            cards=list(cards or []),
            relics=[],
            potions=[],
            purge_available=purge_available,
            purge_cost=75,
        ),
        commands=["choose", "leave", "state"],
        gold=gold,
    )


def _config(tmp_path, *, seed=1, budget=2, trace_name="trace.jsonl"):
    return ExplorationConfig(
        schema_version=CONFIG_SCHEMA_VERSION,
        session_id="session-a",
        seed=seed,
        enabled_categories=("card_reward", "shop"),
        category_rates_bps={"card_reward": 1000, "shop": 1000},
        per_run_alternative_budget=budget,
        trace_path=tmp_path / trace_name,
        manifest_path=tmp_path / "manifest.json",
        source_commit=SOURCE_COMMIT,
    )


def _config_for_arm(tmp_path, proposal, target_action_id, *, run_token="run-1", budget=2):
    trajectory_id = make_trajectory_session_id("session-a", run_token)
    for seed in range(20_000):
        config = _config(tmp_path, seed=seed, budget=budget)
        selection = sample_exploration(
            config,
            proposal,
            trajectory_session_id=trajectory_id,
            decision_index=0,
        )
        if selection.selected_action_id == target_action_id:
            return config
    raise AssertionError(f"could not find deterministic draw for {target_action_id}")


def _leave_reward_screen(game):
    after = deepcopy(game)
    after.screen_type = ScreenType.COMBAT_REWARD
    after.screen = SimpleNamespace(rewards=[])
    after.available_commands = ["proceed", "state"]
    after.cancel_available = False
    after.proceed_available = True
    return after


def _read_records(path):
    raw = Path(path).read_bytes()
    assert raw.endswith(b"\n")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


def test_current_arm_is_persisted_before_return_with_exact_probability(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, adapter.proposal.baseline_action_id)
    controller = NonCombatExplorationController(config)
    trajectory_id = controller.begin_trajectory("run-1")

    result = controller.consider(adapter, game)

    assert result.action is current
    assert result.known_propensity is True
    assert result.selected_action_id == adapter.proposal.baseline_action_id
    assert result.selection.selected_probability_numerator == 9000
    assert result.selection.selected_probability_denominator == 10000
    records = _read_records(config.trace_path)
    assert len(records) == 1
    assert records[0]["record_type"] == "proposed"
    assert records[0]["decision_id"] == result.decision_id
    assert records[0]["trajectory_session_id"] == trajectory_id
    assert records[0]["selection"]["selected_action_id"] == result.selected_action_id
    assert controller.pending_decision_id == result.decision_id


def test_alternative_arm_is_persisted_and_reserves_budget_before_return(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, "card_reward:skip")
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")

    result = controller.consider(adapter, game)

    assert isinstance(result.action, CancelAction)
    assert result.known_propensity is True
    assert result.selected_action_id == "card_reward:skip"
    assert result.selection.selected_probability_numerator == 1000
    assert controller.alternative_attempts == 1
    assert _read_records(config.trace_path)[0]["record_type"] == "proposed"


class _FailingStore:
    def append_proposed(self, _record):
        raise ExplorationPersistenceError("disk unavailable")


def test_proposal_write_failure_returns_unmodified_current_without_claim(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, "card_reward:skip")
    controller = NonCombatExplorationController(config, record_store=_FailingStore())
    controller.begin_trajectory("run-1")

    result = controller.consider(adapter, game)

    assert result.action is current
    assert result.known_propensity is False
    assert result.fallback_reason == "proposal_persistence_failed:disk unavailable"
    assert result.decision_id == ""
    assert controller.alternative_attempts == 0
    assert controller.pending_decision_id is None
    assert not config.trace_path.exists()


def test_record_store_rejects_partial_existing_record(tmp_path):
    trace_path = tmp_path / "partial.jsonl"
    trace_path.write_bytes(b'{"record_type":"proposed"}')

    with pytest.raises(ExplorationPersistenceError, match="partial JSONL record"):
        ExplorationRecordStore(trace_path)


def test_record_store_rejects_duplicate_decision_id(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, adapter.proposal.baseline_action_id)
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    controller.consider(adapter, game)
    record = _read_records(config.trace_path)[0]

    with pytest.raises(ExplorationPersistenceError, match="duplicate decision_id"):
        controller.record_store.append_proposed(record)


def test_alternative_budget_is_not_released_after_rejection(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(
        tmp_path,
        adapter.proposal,
        "card_reward:skip",
        budget=1,
    )
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    first = controller.consider(adapter, game)
    assert first.selected_action_id == "card_reward:skip"

    contradictory = _leave_reward_screen(game)
    contradictory.deck.append(_item("Anger"))
    resolution = controller.resolve_pending(contradictory)
    second = controller.consider(adapter, game)

    assert resolution["status"] == "rejected"
    assert controller.alternative_attempts == 1
    assert second.action is current
    assert second.known_propensity is False
    assert second.fallback_reason == "alternative_attempt_budget_exhausted"
    assert len(_read_records(config.trace_path)) == 2


def test_terminal_pending_decision_is_preserved_as_unresolved(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, adapter.proposal.baseline_action_id)
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    result = controller.consider(adapter, game)

    resolution = controller.end_trajectory()

    assert resolution["decision_id"] == result.decision_id
    assert resolution["status"] == "terminal_unresolved"
    assert controller.pending_decision_id is None
    assert _read_records(config.trace_path)[-1]["status"] == "terminal_unresolved"


def test_pending_decision_can_be_marked_superseded(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, adapter.proposal.baseline_action_id)
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    controller.consider(adapter, game)

    resolution = controller.resolve_pending(game, superseded=True)

    assert resolution["status"] == "superseded"
    assert resolution["reason"] == "new_decision_before_unique_confirmation"


def test_card_take_confirms_only_after_unique_deck_transition(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, adapter.proposal.baseline_action_id)
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    controller.consider(adapter, game)
    after = _leave_reward_screen(game)
    after.deck.append(_item("Anger"))

    resolution = controller.resolve_pending(after)

    assert resolution["status"] == "confirmed"
    assert resolution["reason"] == "selected_card_added_once"


def test_card_skip_confirms_only_after_reward_exit_without_deck_change(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, "card_reward:skip")
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    controller.consider(adapter, game)

    resolution = controller.resolve_pending(_leave_reward_screen(game))

    assert resolution["status"] == "confirmed"
    assert resolution["reason"] == "reward_exited_without_deck_change"


def test_shop_purchase_confirms_from_exact_gold_and_inventory_transition(tmp_path):
    anger = _item("Anger", price=50)
    game = _shop_game(cards=[anger], gold=150)
    current = BuyCardAction(anger)
    adapter = build_shop_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, adapter.proposal.baseline_action_id)
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    controller.consider(adapter, game)
    after = deepcopy(game)
    after.gold = 100
    after.screen.cards = []

    resolution = controller.resolve_pending(after)

    assert resolution["status"] == "confirmed"
    assert resolution["reason"] == "shop_purchase_uniquely_observed"


def test_shop_purge_confirms_from_purge_grid_transition(tmp_path):
    game = _shop_game(purge_available=True, gold=150)
    current = ChooseAction(name="purge")
    adapter = build_shop_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, "shop:purge")
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    controller.consider(adapter, game)
    after = deepcopy(game)
    after.screen_type = ScreenType.GRID
    after.screen = SimpleNamespace(
        cards=deepcopy(game.deck),
        selected_cards=[],
        num_cards=1,
        for_purge=True,
        for_upgrade=False,
        for_transform=False,
    )

    resolution = controller.resolve_pending(after)

    assert resolution["status"] == "confirmed"
    assert resolution["reason"] == "purge_grid_opened"


def test_shop_leave_confirms_after_shop_screen_exit(tmp_path):
    anger = _item("Anger", price=50)
    game = _shop_game(cards=[anger], gold=150)
    current = BuyCardAction(anger)
    adapter = build_shop_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, "shop:leave")
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    result = controller.consider(adapter, game)
    assert isinstance(result.action, LeaveAction)
    after = deepcopy(game)
    after.screen_type = ScreenType.SHOP_ROOM
    after.screen = SimpleNamespace()

    resolution = controller.resolve_pending(after)

    assert resolution["status"] == "confirmed"
    assert resolution["reason"] == "shop_screen_exited"


def test_confirmed_loader_excludes_rejected_and_unresolved_records(tmp_path):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    config = _config_for_arm(tmp_path, adapter.proposal, adapter.proposal.baseline_action_id)
    controller = NonCombatExplorationController(config)
    controller.begin_trajectory("run-1")
    confirmed_result = controller.consider(adapter, game)
    confirmed_after = _leave_reward_screen(game)
    confirmed_after.deck.append(_item("Anger"))
    controller.resolve_pending(confirmed_after)

    controller.begin_trajectory("run-2")
    unresolved_result = controller.consider(adapter, game)
    controller.end_trajectory()

    executed = confirmed_exploration_decisions(config.trace_path)

    assert [row["decision_id"] for row in executed] == [confirmed_result.decision_id]
    assert executed[0]["executed_known_propensity"] is True
    assert unresolved_result.decision_id not in {
        row["decision_id"] for row in executed
    }


def test_stable_trajectory_and_decision_ids_are_namespaced_and_replayable():
    trajectory_a = make_trajectory_session_id("session-a", "run-123")
    trajectory_b = make_trajectory_session_id("session-a", "run-124")

    assert trajectory_a == make_trajectory_session_id("session-a", "run-123")
    assert trajectory_a != trajectory_b
    assert make_decision_id("session-a", trajectory_a, 3, "f" * 64) == make_decision_id(
        "session-a", trajectory_a, 3, "f" * 64
    )
    assert make_decision_id("session-a", trajectory_a, 3, "f" * 64) != make_decision_id(
        "session-a", trajectory_a, 4, "f" * 64
    )


def test_manifest_is_created_once_with_config_and_source_hashes(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"schema_version":"test"}\n', encoding="utf-8")
    config = ExplorationConfig(
        schema_version=CONFIG_SCHEMA_VERSION,
        session_id="session-a",
        seed=7,
        enabled_categories=("card_reward",),
        category_rates_bps={"card_reward": 500},
        per_run_alternative_budget=1,
        trace_path=tmp_path / "trace.jsonl",
        manifest_path=tmp_path / "manifest.json",
        source_commit=SOURCE_COMMIT,
        source_path=config_path,
    )

    manifest = create_exploration_session_manifest(
        config,
        source_clean=True,
        python_executable=sys.executable,
        command=[sys.executable, "main.py", "--agent", "optimized"],
        isolation_hashes={"communication_mod_config": "b" * 64},
    )
    on_disk = json.loads(config.manifest_path.read_text(encoding="utf-8"))

    assert on_disk == manifest
    assert on_disk["session_id"] == "session-a"
    assert on_disk["effective_config_hash"]
    assert on_disk["config_file_sha256"]
    assert on_disk["source"]["commit"] == SOURCE_COMMIT
    assert on_disk["source"]["tracked_clean"] is True
    assert on_disk["manifest_hash"]
    with pytest.raises(ExplorationPersistenceError, match="manifest already exists"):
        create_exploration_session_manifest(
            config,
            source_clean=True,
            python_executable=sys.executable,
            command=[sys.executable, "main.py"],
            isolation_hashes={},
        )
