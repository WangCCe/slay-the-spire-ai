from types import SimpleNamespace

import pytest

from scripts.run_training_batch import build_child_env
from spirecomm.ai.rl.v2.latent_gated_live_candidate import (
    REGISTRATION_ENV as CANDIDATE_REGISTRATION_ENV,
)
from spirecomm.ai.rl.v2.latent_gated_live_shadow import REGISTRATION_ENV


def _args(**overrides):
    values = {
        "combat_latent_candidate_registration": None,
        "combat_latent_shadow_registration": None,
        "game_dir": r"D:\SteamLibrary\steamapps\common\SlayTheSpire",
        "noncombat_exploration_config": None,
        "skip_decision_trace": True,
        "skip_sim_divergence_trace": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_child_env_forwards_explicit_combat_latent_shadow_registration(
    monkeypatch,
):
    monkeypatch.delenv(REGISTRATION_ENV, raising=False)
    registration = r"D:\tmp\combat-latent-shadow-registration.json"

    env = build_child_env(
        _args(combat_latent_shadow_registration=registration)
    )

    assert env[REGISTRATION_ENV] == registration


def test_child_env_clears_ambient_combat_latent_shadow_registration(
    monkeypatch,
):
    monkeypatch.setenv(REGISTRATION_ENV, r"D:\tmp\stale-registration.json")

    env = build_child_env(_args())

    assert REGISTRATION_ENV not in env


def test_child_env_forwards_explicit_combat_latent_candidate_registration(
    monkeypatch,
):
    monkeypatch.delenv(CANDIDATE_REGISTRATION_ENV, raising=False)
    registration = r"D:\tmp\combat-latent-candidate-registration.json"

    env = build_child_env(
        _args(combat_latent_candidate_registration=registration)
    )

    assert env[CANDIDATE_REGISTRATION_ENV] == registration


def test_child_env_clears_ambient_combat_latent_candidate_registration(
    monkeypatch,
):
    monkeypatch.setenv(
        CANDIDATE_REGISTRATION_ENV, r"D:\tmp\stale-candidate-registration.json"
    )

    env = build_child_env(_args())

    assert CANDIDATE_REGISTRATION_ENV not in env


def test_child_env_rejects_simultaneous_shadow_and_candidate_registrations():
    with pytest.raises(ValueError, match="mutually exclusive"):
        build_child_env(
            _args(
                combat_latent_shadow_registration="shadow.json",
                combat_latent_candidate_registration="candidate.json",
            )
        )
