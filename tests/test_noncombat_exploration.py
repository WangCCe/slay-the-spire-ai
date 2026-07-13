import json
from dataclasses import replace
from dataclasses import FrozenInstanceError

import pytest


def _config_payload(tmp_path, **overrides):
    payload = {
        "schema_version": "noncombat-exploration-config-v1",
        "session_id": "fixture-session-001",
        "seed": 17,
        "enabled_categories": ["card_reward", "shop"],
        "category_rates_bps": {"card_reward": 250, "shop": 1000},
        "per_run_alternative_budget": 2,
        "trace_path": str(tmp_path / "exploration.jsonl"),
        "manifest_path": str(tmp_path / "session.json"),
        "source_commit": "a" * 40,
    }
    payload.update(overrides)
    return payload


def test_missing_exploration_environment_disables_without_artifacts(tmp_path):
    from spirecomm.ai.noncombat_exploration import (
        load_exploration_config_from_env,
    )

    config = load_exploration_config_from_env({})

    assert config is None
    assert list(tmp_path.iterdir()) == []


def test_valid_exploration_configuration_is_deeply_immutable(tmp_path):
    from spirecomm.ai.noncombat_exploration import parse_exploration_config

    config = parse_exploration_config(_config_payload(tmp_path))

    assert config.schema_version == "noncombat-exploration-config-v1"
    assert config.session_id == "fixture-session-001"
    assert config.enabled_categories == ("card_reward", "shop")
    assert config.rate_bps("card_reward") == 250
    assert config.rate_bps("shop") == 1000
    assert config.per_run_alternative_budget == 2
    assert config.trace_path == (tmp_path / "exploration.jsonl").resolve()
    assert config.manifest_path == (tmp_path / "session.json").resolve()

    with pytest.raises(FrozenInstanceError):
        config.seed = 99
    with pytest.raises(TypeError):
        config.category_rates_bps["shop"] = 0


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"schema_version": "v0"}, "schema_version"),
        ({"session_id": "bad session"}, "session_id"),
        ({"seed": True}, "seed"),
        ({"enabled_categories": []}, "enabled_categories"),
        ({"enabled_categories": ["shop", "shop"]}, "duplicate"),
        ({"enabled_categories": ["event"]}, "executable category"),
        (
            {
                "enabled_categories": ["shop"],
                "category_rates_bps": {"shop": 1001},
            },
            "1,000",
        ),
        (
            {
                "enabled_categories": ["shop"],
                "category_rates_bps": {},
            },
            "exactly match",
        ),
        ({"per_run_alternative_budget": 3}, "budget"),
        ({"source_commit": "abc123"}, "source_commit"),
    ],
)
def test_exploration_configuration_rejects_unsafe_values(
    tmp_path, overrides, message
):
    from spirecomm.ai.noncombat_exploration import (
        ExplorationConfigurationError,
        parse_exploration_config,
    )

    with pytest.raises(ExplorationConfigurationError, match=message):
        parse_exploration_config(_config_payload(tmp_path, **overrides))


@pytest.mark.parametrize("missing_key", ["session_id", "source_commit", "trace_path", "manifest_path"])
def test_exploration_configuration_requires_provenance_fields(tmp_path, missing_key):
    from spirecomm.ai.noncombat_exploration import (
        ExplorationConfigurationError,
        parse_exploration_config,
    )

    payload = _config_payload(tmp_path)
    del payload[missing_key]

    with pytest.raises(ExplorationConfigurationError, match=missing_key):
        parse_exploration_config(payload)


def test_exploration_configuration_rejects_output_path_collisions(tmp_path):
    from spirecomm.ai.noncombat_exploration import (
        ExplorationConfigurationError,
        parse_exploration_config,
    )

    shared = str(tmp_path / "shared.json")

    with pytest.raises(ExplorationConfigurationError, match="distinct"):
        parse_exploration_config(
            _config_payload(tmp_path, trace_path=shared, manifest_path=shared)
        )


def test_loading_configuration_rejects_config_output_collision(tmp_path):
    from spirecomm.ai.noncombat_exploration import (
        ExplorationConfigurationError,
        load_exploration_config,
    )

    config_path = tmp_path / "exploration-config.json"
    payload = _config_payload(tmp_path, trace_path=str(config_path))
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExplorationConfigurationError, match="configuration path"):
        load_exploration_config(config_path)


def test_loading_configuration_from_environment_is_read_only(tmp_path):
    from spirecomm.ai.noncombat_exploration import (
        CONFIG_ENV,
        load_exploration_config_from_env,
    )

    config_path = tmp_path / "exploration-config.json"
    payload = _config_payload(tmp_path)
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    config = load_exploration_config_from_env({CONFIG_ENV: str(config_path)})

    assert config is not None
    assert config.source_path == config_path.resolve()
    assert not config.trace_path.exists()
    assert not config.manifest_path.exists()


def _proposal(*, category="shop", state=None, candidates=None, **overrides):
    from spirecomm.ai.noncombat_exploration import (
        ExplorationCandidate,
        NonCombatProposal,
    )

    if candidates is None:
        candidates = (
            ExplorationCandidate(
                action_id=f"{category}:buy:slot:0",
                kind="buy_card",
                label="Buy Pommel Strike",
                raw={"slot": 0, "price": 50},
            ),
            ExplorationCandidate(
                action_id=f"{category}:leave",
                kind="leave",
                label="Leave",
                raw={"command": "cancel"},
            ),
        )
    values = {
        "category": category,
        "baseline_action_id": f"{category}:buy:slot:0",
        "alternative_action_id": f"{category}:leave",
        "candidates": candidates,
        "state": state or {"floor": 4, "gold": 99, "deck": ["Strike", "Defend"]},
        "execution_eligible": True,
        "rollout_mode": "executable",
    }
    values.update(overrides)
    return NonCombatProposal(**values)


def test_proposal_is_deeply_immutable_and_has_stable_state_hash():
    from spirecomm.ai.noncombat_exploration import ExplorationCandidate

    first = _proposal(state={"gold": 99, "floor": 4})
    second = _proposal(state={"floor": 4, "gold": 99})

    assert first.state_hash == second.state_hash
    assert tuple(candidate.action_id for candidate in first.candidates) == (
        "shop:buy:slot:0",
        "shop:leave",
    )
    with pytest.raises(FrozenInstanceError):
        first.category = "event"
    with pytest.raises(TypeError):
        first.state["gold"] = 0
    with pytest.raises(TypeError):
        first.candidates[0].raw["price"] = 0

    reordered_candidates = (
        first.candidates[1],
        ExplorationCandidate(
            action_id="shop:buy:slot:0",
            kind="buy_card",
            label="Buy Pommel Strike",
            raw={"price": 50, "slot": 0},
        ),
    )
    assert _proposal(candidates=reordered_candidates).state_hash != first.state_hash


def test_proposal_rejects_duplicate_or_unmapped_candidate_ids():
    from spirecomm.ai.noncombat_exploration import (
        ExplorationCandidate,
        ExplorationProposalError,
    )

    duplicate = ExplorationCandidate(
        action_id="shop:buy:slot:0",
        kind="leave",
        label="duplicate",
    )
    with pytest.raises(ExplorationProposalError, match="duplicate candidate action_id"):
        _proposal(candidates=(_proposal().candidates[0], duplicate))

    with pytest.raises(ExplorationProposalError, match="baseline_action_id"):
        _proposal(baseline_action_id="shop:missing")
    with pytest.raises(ExplorationProposalError, match="alternative_action_id"):
        _proposal(alternative_action_id="shop:missing")


def test_exact_distribution_and_selected_probability_are_candidate_legal(tmp_path):
    from spirecomm.ai.noncombat_exploration import (
        parse_exploration_config,
        sample_exploration,
    )

    config = parse_exploration_config(
        _config_payload(
            tmp_path,
            enabled_categories=["shop"],
            category_rates_bps={"shop": 1000},
        )
    )
    proposal = _proposal()
    selections = [
        sample_exploration(
            config,
            proposal,
            trajectory_session_id="trajectory-001",
            decision_index=index,
        )
        for index in range(500)
    ]

    first_distribution = selections[0].distribution
    assert [entry.action_id for entry in first_distribution] == [
        proposal.baseline_action_id,
        proposal.alternative_action_id,
    ]
    assert [
        (entry.numerator, entry.denominator) for entry in first_distribution
    ] == [(9000, 10000), (1000, 10000)]
    assert sum(entry.numerator for entry in first_distribution) == 10000
    assert all(selection.selected_action_id in proposal.candidate_ids for selection in selections)
    assert {selection.selected_action_id for selection in selections} == set(
        proposal.candidate_ids
    )
    for selection in selections:
        selected = next(
            entry
            for entry in selection.distribution
            if entry.action_id == selection.selected_action_id
        )
        assert selection.selected_probability_numerator == selected.numerator
        assert selection.selected_probability_denominator == selected.denominator
        assert selection.selected_action_probability == selected.numerator / selected.denominator
        assert 0 <= selection.draw_bucket < 10000


def test_sampling_is_byte_stable_and_replay_detects_tampering(tmp_path):
    from spirecomm.ai.noncombat_exploration import (
        parse_exploration_config,
        sample_exploration,
        verify_exploration_selection,
    )

    config = parse_exploration_config(
        _config_payload(
            tmp_path,
            enabled_categories=["shop"],
            category_rates_bps={"shop": 250},
        )
    )
    proposal = _proposal()
    kwargs = {
        "trajectory_session_id": "trajectory-001",
        "decision_index": 7,
    }

    first = sample_exploration(config, proposal, **kwargs)
    second = sample_exploration(config, proposal, **kwargs)

    assert first == second
    assert first.canonical_json() == second.canonical_json()
    assert verify_exploration_selection(config, proposal, first, **kwargs).valid is True

    other_action = next(
        action_id
        for action_id in proposal.candidate_ids
        if action_id != first.selected_action_id
    )
    tampered = replace(first, selected_action_id=other_action)
    replay = verify_exploration_selection(config, proposal, tampered, **kwargs)
    assert replay.valid is False
    assert replay.errors == ("selected_action_id_mismatch",)


def test_zero_rate_is_deterministic_current_with_exact_probability(tmp_path):
    from spirecomm.ai.noncombat_exploration import (
        parse_exploration_config,
        sample_exploration,
    )

    config = parse_exploration_config(
        _config_payload(
            tmp_path,
            enabled_categories=["shop"],
            category_rates_bps={"shop": 0},
        )
    )

    selection = sample_exploration(
        config,
        _proposal(),
        trajectory_session_id="trajectory-001",
        decision_index=0,
    )

    assert selection.selected_action_id == "shop:buy:slot:0"
    assert selection.selected_probability_numerator == 10000
    assert selection.selected_probability_denominator == 10000
    assert selection.selected_action_probability == 1.0


@pytest.mark.parametrize(
    "proposal_kwargs",
    [
        pytest.param(
            {"category": "card_reward"},
            id="disabled-category",
        ),
        pytest.param(
            {
                "execution_eligible": False,
                "rollout_mode": "ineligible",
                "ineligibility_reason": "missing_abstention",
            },
            id="ineligible",
        ),
    ],
)
def test_sampling_rejects_disabled_or_ineligible_proposals(tmp_path, proposal_kwargs):
    from spirecomm.ai.noncombat_exploration import (
        ExplorationSamplingError,
        parse_exploration_config,
        sample_exploration,
    )

    config = parse_exploration_config(
        _config_payload(
            tmp_path,
            enabled_categories=["shop"],
            category_rates_bps={"shop": 100},
        )
    )
    proposal = _proposal(**proposal_kwargs)

    with pytest.raises(ExplorationSamplingError):
        sample_exploration(
            config,
            proposal,
            trajectory_session_id="trajectory-001",
            decision_index=0,
        )
