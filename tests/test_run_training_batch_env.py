from types import SimpleNamespace

from scripts.run_training_batch import build_child_env
from spirecomm.ai.rl.v2.latent_gated_live_shadow import REGISTRATION_ENV


def _args(**overrides):
    values = {
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
