import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

import analysis_scripts.combat_lightspeed_production_candidate as candidate_module
from analysis_scripts.combat_lightspeed_bridge import sha256_file
from analysis_scripts.combat_lightspeed_production_candidate import (
    PACKAGED_FILENAME,
    publish_production_candidate,
)
from analysis_scripts.combat_lightspeed_production_shadow import (
    expected_rl_v2_metadata,
    load_production_checkpoint,
)
from analysis_scripts.combat_lightspeed_training_smoke import (
    create_fresh_trainer,
    parameter_sha256,
)
from spirecomm.ai.rl.checkpoint_io import (
    load_torch_checkpoint,
    save_torch_checkpoint,
)
from spirecomm.ai.rl.v2.agent import RLAgentV2
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper


def _write_items(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cards": [{"id": "Strike"}],
                "potions": [{"id": "Fire Potion"}],
                "relics": [{"id": "Burning Blood"}],
            }
        ),
        encoding="utf-8",
    )


def _write_production(path: Path, items_path: Path, *, metadata_override=None):
    mapper = build_id_mapper(str(items_path))
    trainer = create_fresh_trainer(
        mapper,
        seed=101,
        batch_size=2,
        learning_starts=2,
    )
    state = copy.deepcopy(trainer.online_network.state_dict())
    metadata = expected_rl_v2_metadata(mapper)
    metadata.update(metadata_override or {})
    save_torch_checkpoint(
        {
            "checkpoint_schema_version": 2,
            "checkpoint_kind": "weights",
            "metadata": metadata,
            "rl_space_version": "v2",
            "online_network_state_dict": state,
            "episode": 0,
            "provenance": {"experiment_id": "test-production-parent"},
        },
        str(path),
    )
    return state


def _candidate_state(items_path: Path):
    mapper = build_id_mapper(str(items_path))
    trainer = create_fresh_trainer(
        mapper,
        seed=102,
        batch_size=2,
        learning_starts=2,
    )
    state = copy.deepcopy(trainer.online_network.state_dict())
    first = next(iter(state))
    state[first].view(-1)[0] += 0.125
    return state


def _write_candidate(
    path: Path,
    state,
    *,
    production_compatible=False,
    parameter_binding=None,
    checkpoint_kind="simulator_training_smoke",
) -> None:
    save_torch_checkpoint(
        {
            "checkpoint_schema_version": 0,
            "checkpoint_kind": checkpoint_kind,
            "source_type": "sts_lightspeed_combat_simulation",
            "production_compatible": production_compatible,
            "online_network_state_dict": copy.deepcopy(state),
            "metadata": {
                "authority": {"simulator_fitting": True, "promotion": False},
                "source_binding": {
                    "candidate_parameter_sha256": (
                        parameter_binding or parameter_sha256(state)
                    )
                },
            },
        },
        str(path),
    )


def _write_confirmation(path: Path, candidate_sha256: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "test-confirmation-v1",
                "candidates": [
                    {"label": "guarded_control_candidate", "sha256": candidate_sha256}
                ],
                "pairwise": {"terminal_profile_count": 100},
            }
        ),
        encoding="utf-8",
    )


def _fixture(tmp_path: Path, *, metadata_override=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    items_path = tmp_path / "items.json"
    production_path = tmp_path / "production.pth"
    candidate_path = tmp_path / "candidate.pth"
    confirmation_path = tmp_path / "confirmation.json"
    _write_items(items_path)
    production_state = _write_production(
        production_path,
        items_path,
        metadata_override=metadata_override,
    )
    candidate_state = _candidate_state(items_path)
    _write_candidate(candidate_path, candidate_state)
    _write_confirmation(confirmation_path, sha256_file(candidate_path))
    return {
        "items": items_path,
        "production": production_path,
        "candidate": candidate_path,
        "confirmation": confirmation_path,
        "production_state": production_state,
        "candidate_state": candidate_state,
        "output": tmp_path / "packaged",
    }


def _publish(paths, **overrides):
    arguments = {
        "output_dir": paths["output"],
        "simulator_candidate": paths["candidate"],
        "expected_candidate_sha256": sha256_file(paths["candidate"]),
        "production_parent": paths["production"],
        "expected_parent_sha256": sha256_file(paths["production"]),
        "items_json": paths["items"],
        "expected_items_sha256": sha256_file(paths["items"]),
        "confirmation_report": paths["confirmation"],
        "expected_confirmation_sha256": sha256_file(paths["confirmation"]),
        "source_commit": "a" * 40,
        "probe_count": 8,
    }
    arguments.update(overrides)
    return publish_production_candidate(**arguments)


def test_publication_preserves_candidate_and_loads_as_production_weights(tmp_path):
    paths = _fixture(tmp_path)
    input_hashes = {
        name: sha256_file(paths[name])
        for name in ("items", "production", "candidate", "confirmation")
    }

    report = _publish(paths)

    assert report["verdict"] == "production_candidate_packaging_ready"
    assert report["equivalence"]["passed"] is True
    assert report["equivalence"]["action_mismatch_count"] == 0
    assert report["equivalence"]["max_abs_q_delta"] == 0.0
    assert report["packaged_checkpoint"]["parameter_sha256"] == parameter_sha256(
        paths["candidate_state"]
    )
    packaged_path = paths["output"] / PACKAGED_FILENAME
    packaged = load_torch_checkpoint(str(packaged_path), map_location="cpu")
    assert packaged["checkpoint_schema_version"] == 2
    assert packaged["checkpoint_kind"] == "weights"
    assert packaged["rl_space_version"] == "v2"
    assert "production_compatible" not in packaged
    assert "optimizer_state_dict" not in packaged
    assert parameter_sha256(packaged["online_network_state_dict"]) == parameter_sha256(
        paths["candidate_state"]
    )
    mapper = build_id_mapper(str(paths["items"]))
    strict = load_production_checkpoint(
        packaged_path,
        expected_sha256=sha256_file(packaged_path),
        id_mapper=mapper,
    )
    assert strict["parameter_sha256"] == parameter_sha256(paths["candidate_state"])
    agent = RLAgentV2(
        model_path=str(packaged_path),
        training=False,
        device="cpu",
        id_mapper=mapper,
    )
    assert parameter_sha256(agent.network.state_dict()) == parameter_sha256(
        paths["candidate_state"]
    )
    manifest = json.loads(
        (paths["output"] / "manifest.json").read_text(encoding="utf-8")
    )
    assert set(manifest["artifacts"]) == {
        PACKAGED_FILENAME,
        "report.json",
        "summary.md",
    }
    for name, binding in manifest["artifacts"].items():
        assert sha256_file(paths["output"] / name) == binding["sha256"]
        assert (paths["output"] / name).stat().st_size == binding["size_bytes"]
    assert {
        name: sha256_file(paths[name])
        for name in ("items", "production", "candidate", "confirmation")
    } == input_hashes


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("production_compatible", "production-compatible"),
        ("wrong_kind", "kind"),
        ("wrong_parameter_binding", "parameter"),
        ("missing_tensor", "structure"),
        ("nonfinite", "finite"),
        ("unbound_confirmation", "confirmation"),
    ],
)
def test_invalid_candidate_or_confirmation_fails_before_publication(
    tmp_path,
    mutation,
    message,
):
    paths = _fixture(tmp_path)
    state = copy.deepcopy(paths["candidate_state"])
    if mutation == "production_compatible":
        _write_candidate(paths["candidate"], state, production_compatible=True)
    elif mutation == "wrong_kind":
        _write_candidate(paths["candidate"], state, checkpoint_kind="weights")
    elif mutation == "wrong_parameter_binding":
        _write_candidate(paths["candidate"], state, parameter_binding="f" * 64)
    elif mutation == "missing_tensor":
        state.pop(next(iter(state)))
        _write_candidate(paths["candidate"], state)
    elif mutation == "nonfinite":
        state[next(iter(state))].view(-1)[0] = float("nan")
        _write_candidate(paths["candidate"], state)
    elif mutation == "unbound_confirmation":
        _write_confirmation(paths["confirmation"], "0" * 64)
    if mutation != "unbound_confirmation":
        _write_confirmation(paths["confirmation"], sha256_file(paths["candidate"]))

    with pytest.raises(ValueError, match=message):
        _publish(paths)

    assert not paths["output"].exists()


@pytest.mark.parametrize(
    ("override_name", "message"),
    [
        ("expected_candidate_sha256", "candidate checkpoint hash mismatch"),
        ("expected_parent_sha256", "production checkpoint hash mismatch"),
        ("expected_items_sha256", "items JSON hash mismatch"),
        ("expected_confirmation_sha256", "confirmation report hash mismatch"),
    ],
)
def test_bound_hash_mismatch_fails_before_publication(
    tmp_path,
    override_name,
    message,
):
    paths = _fixture(tmp_path)
    with pytest.raises(ValueError, match=message):
        _publish(paths, **{override_name: "0" * 64})
    assert not paths["output"].exists()


def test_production_metadata_mismatch_fails_before_publication(tmp_path):
    invalid = _fixture(tmp_path / "metadata", metadata_override={"action_dim": 132})
    with pytest.raises(ValueError, match="metadata"):
        _publish(invalid)
    assert not invalid["output"].exists()


def test_existing_output_is_never_replaced(tmp_path):
    paths = _fixture(tmp_path)
    paths["output"].mkdir()
    marker = paths["output"] / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        _publish(paths)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_bound_inputs_are_read_once(tmp_path, monkeypatch):
    paths = _fixture(tmp_path)
    bindings = {
        name: sha256_file(paths[name])
        for name in ("items", "production", "candidate", "confirmation")
    }
    bound = {
        paths[name].resolve()
        for name in ("items", "production", "candidate", "confirmation")
    }
    counts = {path: 0 for path in bound}
    original = Path.read_bytes

    def counted(path):
        resolved = path.resolve()
        if resolved in counts:
            counts[resolved] += 1
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", counted)
    publish_production_candidate(
        paths["output"],
        simulator_candidate=paths["candidate"],
        expected_candidate_sha256=bindings["candidate"],
        production_parent=paths["production"],
        expected_parent_sha256=bindings["production"],
        items_json=paths["items"],
        expected_items_sha256=bindings["items"],
        confirmation_report=paths["confirmation"],
        expected_confirmation_sha256=bindings["confirmation"],
        source_commit="a" * 40,
        probe_count=8,
    )

    assert counts == {path: 1 for path in bound}


def test_failed_equivalence_removes_only_owned_staging(tmp_path, monkeypatch):
    paths = _fixture(tmp_path)

    def failed(*args, **kwargs):
        return {
            "passed": False,
            "parameter_sha256_match": True,
            "action_mismatch_count": 1,
            "max_abs_q_delta": 0.0,
        }

    monkeypatch.setattr(candidate_module, "prove_reload_equivalence", failed)
    with pytest.raises(ValueError, match="equivalence"):
        _publish(paths)

    assert not paths["output"].exists()
    assert not list(tmp_path.glob(".packaged.*.staging"))
    assert paths["candidate"].is_file()
    assert paths["production"].is_file()


def test_preexisting_unique_staging_is_not_deleted(tmp_path, monkeypatch):
    paths = _fixture(tmp_path)
    monkeypatch.setattr(
        candidate_module.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex="fixed"),
    )
    staging = tmp_path / ".packaged.fixed.staging"
    staging.mkdir()
    marker = staging / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        _publish(paths)

    assert marker.read_text(encoding="utf-8") == "keep"
