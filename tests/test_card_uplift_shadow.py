import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import main
from scripts.run_training_batch import build_child_env
from spirecomm.ai import card_uplift_shadow as shadow
from spirecomm.communication.action import CancelAction, CardRewardAction
from spirecomm.spire.screen import ScreenType


def _card(name):
    return SimpleNamespace(name=name, upgrades=0, misc=0)


def _game(*, seed=101, cards=None, can_bowl=False, can_skip=True, in_combat=False):
    cards = list(cards or [_card("Anger"), _card("Cleave"), _card("Shrug It Off")])
    return SimpleNamespace(
        act=1,
        act_boss="The Guardian",
        ascension_level=0,
        current_hp=61,
        deck=[_card("Strike"), _card("Defend")],
        floor=3,
        gold=99,
        has_emerald_key=False,
        has_ruby_key=False,
        has_sapphire_key=False,
        in_combat=in_combat,
        map=None,
        max_hp=80,
        monsters=[],
        potions=[],
        relics=[],
        room_type="MONSTER",
        screen=SimpleNamespace(cards=cards, can_bowl=can_bowl, can_skip=can_skip),
        screen_type=ScreenType.CARD_REWARD,
        seed=seed,
    )


def _config(tmp_path):
    binding = {"path": "input.json", "sha256": "a" * 64, "size_bytes": 1}
    return {
        "authority": copy.deepcopy(shadow.AUTHORITY),
        "entry_checkpoint": copy.deepcopy(binding),
        "maximum_games": 5,
        "output_path": (tmp_path / "shadow.jsonl").as_posix(),
        "projection_version": shadow.PROJECTION_VERSION,
        "residual_model": copy.deepcopy(binding),
        "schema_version": shadow.CONFIG_SCHEMA_VERSION,
        "source": {
            "bindings": {name: copy.deepcopy(binding) for name in shadow.SOURCE_PATHS},
            "commit": "b" * 40,
            "repo_root": tmp_path.as_posix(),
        },
    }


def _runtime(tmp_path):
    runtime = shadow.CardUpliftShadowRuntime.__new__(shadow.CardUpliftShadowRuntime)
    runtime.config = shadow.validate_configuration(_config(tmp_path))
    runtime.output_path = tmp_path / "shadow.jsonl"
    runtime.config_sha256 = hashlib.sha256(
        shadow._canonical_bytes(runtime.config)
    ).hexdigest()
    runtime.row_schema_version = shadow.ROW_SCHEMA_VERSION
    runtime.run_key = None
    runtime.run_count = 0
    runtime.last_floor = -1
    runtime.disabled = False
    runtime.decision_count = 0
    runtime.current_map_node = None
    runtime.encounter = "INVALID"
    runtime.seen = set()
    runtime._score = lambda snapshot, candidates: {
        "base_scores": [0.1, 0.2, 0.3, 0.0],
        "candidate_action_ids": [row["action_id"] for row in candidates],
        "composed_scores": [0.1, 0.2, 0.3, 0.0],
        "shadow_action_id": candidates[2]["action_id"],
        "source_sha256": "c" * 64,
        "unseen_take_actions": 0,
    }
    return runtime


def _canary_config(tmp_path):
    config = _config(tmp_path)
    config["authority"] = copy.deepcopy(shadow.CANARY_AUTHORITY)
    config["maximum_games"] = 3
    config["output_path"] = (tmp_path / "canary.jsonl").as_posix()
    config["schema_version"] = shadow.CANARY_CONFIG_SCHEMA_VERSION
    return config


def _evaluation_config(tmp_path, maximum_games=10):
    config = _canary_config(tmp_path)
    config["maximum_games"] = maximum_games
    config["output_path"] = (tmp_path / "evaluation.jsonl").as_posix()
    config["schema_version"] = shadow.EVALUATION_CONFIG_SCHEMA_VERSION
    return config


def _canary_runtime(tmp_path):
    runtime = shadow.CardUpliftCanaryRuntime.__new__(shadow.CardUpliftCanaryRuntime)
    runtime.config = shadow.validate_canary_configuration(_canary_config(tmp_path))
    runtime.output_path = tmp_path / "canary.jsonl"
    runtime.config_sha256 = hashlib.sha256(
        shadow._canonical_bytes(runtime.config)
    ).hexdigest()
    runtime.row_schema_version = shadow.CANARY_ROW_SCHEMA_VERSION
    runtime.run_key = None
    runtime.run_count = 0
    runtime.last_floor = -1
    runtime.disabled = False
    runtime.decision_count = 0
    runtime.current_map_node = None
    runtime.encounter = "INVALID"
    runtime.seen = set()
    runtime._score = lambda snapshot, candidates: {
        "base_scores": [0.1, 0.2, 0.3, 0.0],
        "candidate_action_ids": [row["action_id"] for row in candidates],
        "composed_scores": [0.1, 0.2, 0.3, 0.0],
        "shadow_action_id": candidates[2]["action_id"],
        "source_sha256": "c" * 64,
        "unseen_take_actions": 0,
    }
    return runtime


def _rows(path):
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines()]


def test_absent_config_keeps_main_and_runtime_inert(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("shadow runtime was constructed")

    monkeypatch.setattr(shadow, "CardUpliftShadowRuntime", forbidden)

    assert shadow.initialize_card_uplift_shadow_runtime(environ={}) is None
    assert main.initialize_card_uplift_shadow_if_configured(environ={}) is None


def test_configuration_rejects_authority_and_source_drift(tmp_path):
    config = _config(tmp_path)
    config["authority"]["action_selection"] = True
    with pytest.raises(shadow.CardUpliftShadowError, match="authority"):
        shadow.validate_configuration(config)


def test_canary_configuration_requires_action_authority_and_three_games(tmp_path):
    config = _canary_config(tmp_path)
    assert shadow.validate_canary_configuration(config) == config

    config["maximum_games"] = 4
    with pytest.raises(shadow.CardUpliftShadowError, match="game ceiling"):
        shadow.validate_canary_configuration(config)

    config = _canary_config(tmp_path)
    config["authority"]["action_selection"] = False
    with pytest.raises(shadow.CardUpliftShadowError, match="authority"):
        shadow.validate_canary_configuration(config)

    config = _config(tmp_path)
    config["source"]["bindings"].pop(shadow.SOURCE_PATHS[-1])
    with pytest.raises(shadow.CardUpliftShadowError, match="source"):
        shadow.validate_configuration(config)


@pytest.mark.parametrize("maximum_games", (1, 10, 25))
def test_evaluation_configuration_accepts_bounded_game_ceiling(
    tmp_path, maximum_games
):
    config = _evaluation_config(tmp_path, maximum_games)

    assert shadow.validate_evaluation_configuration(config) == config


@pytest.mark.parametrize("maximum_games", (False, 0, 26, 1.5))
def test_evaluation_configuration_rejects_invalid_game_ceiling(
    tmp_path, maximum_games
):
    with pytest.raises(shadow.CardUpliftShadowError, match="game ceiling"):
        shadow.validate_evaluation_configuration(
            _evaluation_config(tmp_path, maximum_games)
        )


def test_canary_torch_threads_are_capped_without_raising_lower_settings(monkeypatch):
    import torch

    active = {"threads": 8}

    monkeypatch.setattr(torch, "get_num_threads", lambda: active["threads"])
    monkeypatch.setattr(
        torch, "set_num_threads", lambda value: active.update(threads=value)
    )

    assert shadow._configure_canary_torch_threads() == 2
    active["threads"] = 1
    assert shadow._configure_canary_torch_threads() == 1


def test_project_live_card_reward_builds_bounded_api_v3_shape():
    snapshot, candidates, shifts = shadow.project_live_card_reward(
        _game(),
        decision_count=7,
        current_map_node=(2, 3, "M"),
        encounter="JAW_WORM",
    )

    assert snapshot["adapter_api_version"] == "sts-lightspeed-noncombat-adapter-v3"
    assert snapshot["decision_count"] == 7
    assert snapshot["state"]["cur_map_node"] == {"x": 2, "y": 3}
    assert [row["kind"] for row in candidates] == ["take", "take", "take", "skip"]
    assert shifts == shadow.KNOWN_PROJECTION_SHIFTS


@pytest.mark.parametrize(
    ("game", "reason"),
    (
        (_game(cards=[_card("Anger"), _card("Cleave")]), "card_count_not_three"),
        (_game(can_bowl=True), "singing_bowl_present"),
        (_game(can_skip=False), "card_reward_cannot_skip"),
        (_game(in_combat=True), "generated_combat_card_choice"),
    ),
)
def test_project_live_card_reward_rejects_unsupported_boundaries(game, reason):
    with pytest.raises(shadow.CardUpliftShadowError, match=reason):
        shadow.project_live_card_reward(
            game,
            decision_count=0,
            current_map_node=None,
            encounter="INVALID",
        )


def test_complete_row_preserves_current_action_and_deduplicates(tmp_path):
    runtime = _runtime(tmp_path)
    game = _game()
    calls = 0
    actions = []

    def current(_game):
        nonlocal calls
        calls += 1
        action = CardRewardAction(game.screen.cards[0])
        actions.append(action)
        return action

    wrapped = runtime.wrap_state_callback(current)
    first = wrapped(game)
    second = wrapped(game)

    assert calls == 2
    assert first is actions[0]
    assert second is actions[1]
    rows = _rows(runtime.output_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "complete"
    assert rows[0]["action_substituted"] is False
    assert rows[0]["agreement"] is False


def test_canary_substitutes_exact_live_card_and_records_it(tmp_path):
    runtime = _canary_runtime(tmp_path)
    game = _game()
    current = CardRewardAction(game.screen.cards[0])

    selected = runtime.wrap_state_callback(lambda _game: current)(game)

    assert isinstance(selected, CardRewardAction)
    assert selected is not current
    assert selected.name == game.screen.cards[2].name
    row = _rows(runtime.output_path)[0]
    assert row["schema_version"] == shadow.CANARY_ROW_SCHEMA_VERSION
    assert row["action_substituted"] is True
    assert row["agreement"] is False
    assert row["status"] == "complete"


def test_canary_agreement_returns_current_action_object(tmp_path):
    runtime = _canary_runtime(tmp_path)
    game = _game()
    current = CardRewardAction(game.screen.cards[2])

    selected = runtime.wrap_state_callback(lambda _game: current)(game)

    assert selected is current
    assert _rows(runtime.output_path)[0]["action_substituted"] is False


def test_canary_ineligible_falls_back_without_disabling(tmp_path):
    runtime = _canary_runtime(tmp_path)
    game = _game(can_bowl=True)
    current = CardRewardAction(bowl=True)

    selected = runtime.wrap_state_callback(lambda _game: current)(game)

    assert selected is current
    assert runtime.disabled is False
    row = _rows(runtime.output_path)[0]
    assert row["status"] == "ineligible"
    assert row["ineligibility_reason"] == "singing_bowl_present"


def test_canary_scoring_error_falls_back_and_disables_later_intervention(tmp_path):
    runtime = _canary_runtime(tmp_path)
    first_game = _game(seed=301)
    first = CardRewardAction(first_game.screen.cards[0])

    def fail_score(snapshot, candidates):
        raise RuntimeError("scorer failed")

    runtime._score = fail_score
    selected = runtime.wrap_state_callback(lambda _game: first)(first_game)

    assert selected is first
    assert runtime.disabled is True
    assert _rows(runtime.output_path)[0]["status"] == "error"

    second_game = _game(seed=302)
    second = CardRewardAction(second_game.screen.cards[0])
    assert runtime.wrap_state_callback(lambda _game: second)(second_game) is second
    assert len(_rows(runtime.output_path)) == 1


def test_ineligible_and_scoring_error_rows_are_distinct(tmp_path):
    runtime = _runtime(tmp_path)
    bowl_game = _game(seed=201, can_bowl=True)
    runtime.observe(bowl_game, CardRewardAction(bowl=True))

    error_game = _game(seed=202)

    def fail_score(snapshot, candidates):
        raise RuntimeError("scorer failed")

    runtime._score = fail_score
    runtime.observe(error_game, CardRewardAction(error_game.screen.cards[0]))

    rows = _rows(runtime.output_path)
    assert [row["status"] for row in rows] == ["ineligible", "error"]
    assert rows[0]["ineligibility_reason"] == "singing_bowl_present"
    assert rows[1]["error"] == "RuntimeError: scorer failed"


def test_wrapper_fails_open_when_persistence_fails(tmp_path, caplog):
    runtime = _runtime(tmp_path)
    action = CancelAction()

    def fail_observation(game, current_action):
        raise OSError("disk full")

    runtime.observe = fail_observation
    wrapped = runtime.wrap_state_callback(lambda game: action)

    assert wrapped(_game()) is action
    assert "observation failed: disk full" in caplog.text


def test_runtime_stops_observing_after_five_runs(tmp_path):
    runtime = _runtime(tmp_path)
    action = CancelAction()
    for seed in range(1, 7):
        game = _game(seed=seed)
        game.screen_type = ScreenType.NONE
        runtime.observe(game, action)

    assert runtime.run_count == 6
    assert runtime.disabled is True
    assert not runtime.output_path.exists()


def test_canary_stops_intervening_after_three_runs(tmp_path):
    runtime = _canary_runtime(tmp_path)
    action = CancelAction()
    for seed in range(1, 5):
        game = _game(seed=seed)
        game.screen_type = ScreenType.NONE
        runtime._process(game, action, allow_substitution=True)

    assert runtime.run_count == 4
    assert runtime.disabled is True
    assert not runtime.output_path.exists()


def test_batch_child_env_forwards_explicit_shadow_config(monkeypatch):
    monkeypatch.delenv(shadow.CONFIG_ENV, raising=False)
    args = SimpleNamespace(
        card_uplift_shadow_config=r"D:\tmp\card-uplift-shadow.json",
        decision_trace_path=None,
        game_dir=r"D:\SteamLibrary\steamapps\common\SlayTheSpire",
        noncombat_exploration_config=None,
        sim_divergence_trace_path=None,
        skip_decision_trace=True,
        skip_sim_divergence_trace=True,
    )

    env = build_child_env(args)

    assert env[shadow.CONFIG_ENV] == args.card_uplift_shadow_config


def test_batch_child_env_forwards_canary_and_rejects_mode_conflict(monkeypatch):
    args = SimpleNamespace(
        card_uplift_canary_config=r"D:\tmp\card-uplift-canary.json",
        card_uplift_shadow_config=None,
        decision_trace_path=None,
        game_dir=r"D:\SteamLibrary\steamapps\common\SlayTheSpire",
        noncombat_exploration_config=None,
        sim_divergence_trace_path=None,
        skip_decision_trace=True,
        skip_sim_divergence_trace=True,
    )

    env = build_child_env(args)
    assert env[shadow.CANARY_CONFIG_ENV] == args.card_uplift_canary_config

    args.card_uplift_shadow_config = r"D:\tmp\card-uplift-shadow.json"
    with pytest.raises(ValueError, match="mutually exclusive"):
        build_child_env(args)


def test_batch_child_env_forwards_evaluation_and_rejects_three_way_conflict():
    args = SimpleNamespace(
        card_uplift_canary_config=None,
        card_uplift_evaluation_config=r"D:\tmp\card-uplift-evaluation.json",
        card_uplift_shadow_config=None,
        decision_trace_path=None,
        game_dir=r"D:\SteamLibrary\steamapps\common\SlayTheSpire",
        noncombat_exploration_config=None,
        sim_divergence_trace_path=None,
        skip_decision_trace=True,
        skip_sim_divergence_trace=True,
    )

    env = build_child_env(args)
    assert (
        env[shadow.EVALUATION_CONFIG_ENV] == args.card_uplift_evaluation_config
    )

    args.card_uplift_canary_config = r"D:\tmp\card-uplift-canary.json"
    with pytest.raises(ValueError, match="mutually exclusive"):
        build_child_env(args)


def test_main_rejects_shadow_and_canary_mode_conflict():
    with pytest.raises(ValueError, match="mutually exclusive"):
        main.initialize_card_uplift_shadow_if_configured(
            environ={
                shadow.CONFIG_ENV: "shadow.json",
                shadow.CANARY_CONFIG_ENV: "canary.json",
            }
        )


def test_main_dispatches_explicit_evaluation_config(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(
        shadow,
        "initialize_card_uplift_evaluation_runtime",
        lambda *, environ: sentinel,
    )

    assert main.initialize_card_uplift_shadow_if_configured(
        environ={shadow.EVALUATION_CONFIG_ENV: "evaluation.json"}
    ) is sentinel


def test_rl_input_reader_starts_after_callbacks_are_registered():
    source = Path(main.__file__).read_text(encoding="utf-8")
    entrypoint = source.split('if __name__ == "__main__":', 1)[1]

    assert entrypoint.index("register_state_change_callback") < entrypoint.index(
        "coordinator.start_input_thread()"
    )
