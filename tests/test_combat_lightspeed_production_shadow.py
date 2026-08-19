import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

import analysis_scripts.combat_lightspeed_production_shadow as shadow_module
from analysis_scripts.combat_lightspeed_bridge import sha256_file
from analysis_scripts.combat_lightspeed_production_shadow import (
    PRODUCTION_CHECKPOINT_KIND,
    SHADOW_CHECKPOINT_KIND,
    load_production_checkpoint,
    prove_reload_equivalence,
    publish_production_shadow,
)
from analysis_scripts.combat_lightspeed_training_smoke import (
    create_fresh_trainer,
    initialize_trainer,
    load_initial_checkpoint,
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


def _write_production_checkpoint(
    path: Path,
    items_path: Path,
    *,
    metadata_override=None,
    checkpoint_kind=PRODUCTION_CHECKPOINT_KIND,
) -> dict[str, torch.Tensor]:
    mapper = build_id_mapper(str(items_path))
    trainer = create_fresh_trainer(
        mapper,
        seed=20260819,
        batch_size=2,
        learning_starts=2,
    )
    state = copy.deepcopy(trainer.online_network.state_dict())
    metadata = {
        "rl_space_version": "v2",
        "network_type": "dueling",
        "continuous_dim": trainer.continuous_dim,
        "action_dim": trainer.action_dim,
        "card_vocab": mapper.card_vocab_size,
        "potion_vocab": mapper.potion_vocab_size,
        "relic_vocab": mapper.relic_vocab_size,
        "card_slots": trainer.card_slots,
        "potion_slots": trainer.potion_slots,
        "relic_slots": trainer.relic_slots,
    }
    metadata.update(metadata_override or {})
    save_torch_checkpoint(
        {
            "checkpoint_schema_version": 2,
            "checkpoint_kind": checkpoint_kind,
            "rl_space_version": "v2",
            "online_network_state_dict": state,
            "metadata": metadata,
            "episode": 0,
            "provenance": {"experiment_id": "test-production-parent"},
        },
        str(path),
    )
    return state


def _fixture(tmp_path: Path):
    items_path = tmp_path / "items.json"
    source_path = tmp_path / "production.pth"
    _write_items(items_path)
    state = _write_production_checkpoint(source_path, items_path)
    return items_path, source_path, state


def test_publication_preserves_parameters_and_reduces_authority(tmp_path):
    items_path, source_path, state = _fixture(tmp_path)
    output_dir = tmp_path / "shadow"

    report = publish_production_shadow(
        output_dir,
        production_checkpoint=source_path,
        expected_checkpoint_sha256=sha256_file(source_path),
        items_json=items_path,
        expected_items_sha256=sha256_file(items_path),
        source_commit="a" * 40,
        probe_count=8,
    )

    assert report["verdict"] == "production_shadow_ready"
    assert report["equivalence"]["passed"] is True
    assert report["equivalence"]["action_mismatch_count"] == 0
    assert report["equivalence"]["max_abs_q_delta"] == 0.0
    shadow_path = output_dir / "simulator_only_production_shadow.pth"
    shadow = load_torch_checkpoint(str(shadow_path), map_location="cpu")
    assert shadow["checkpoint_kind"] == SHADOW_CHECKPOINT_KIND
    assert shadow["production_compatible"] is False
    assert parameter_sha256(shadow["online_network_state_dict"]) == parameter_sha256(
        state
    )
    assert shadow["metadata"]["source_binding"]["production_checkpoint_sha256"] == (
        sha256_file(source_path)
    )
    assert shadow["metadata"]["authority"]["communication_mod"] is False
    assert shadow["metadata"]["authority"]["simulator_training_parent"] is True
    assert shadow["metadata"]["authority"]["production_agent_loading"] is False
    loaded_parent = load_initial_checkpoint(
        shadow_path,
        expected_sha256=sha256_file(shadow_path),
    )
    mapper = build_id_mapper(str(items_path))
    downstream = create_fresh_trainer(
        mapper,
        seed=20260820,
        batch_size=2,
        learning_starts=2,
        parent_policy_anchor_weight=1.0,
    )
    control, initialization = initialize_trainer(downstream, loaded_parent)
    assert initialization["mode"] == "warm_start"
    assert parameter_sha256(control) == parameter_sha256(state)
    assert parameter_sha256(downstream.target_network.state_dict()) == parameter_sha256(
        state
    )
    assert initialization["parent_policy_anchor_parameter_sha256"] == parameter_sha256(
        state
    )
    with pytest.raises(ValueError, match="Checkpoint version mismatch"):
        RLAgentV2(
            model_path=str(shadow_path),
            training=False,
            device="cpu",
            id_mapper=mapper,
        )
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["artifacts"]) == {
        "report.json",
        "summary.md",
        "simulator_only_production_shadow.pth",
    }
    for name, binding in manifest["artifacts"].items():
        assert sha256_file(output_dir / name) == binding["sha256"]
        assert (output_dir / name).stat().st_size == binding["size_bytes"]


@pytest.mark.parametrize(
    ("expected_hash", "metadata_override", "checkpoint_kind", "message"),
    [
        ("0" * 64, None, PRODUCTION_CHECKPOINT_KIND, "hash mismatch"),
        (None, {"action_dim": 132}, PRODUCTION_CHECKPOINT_KIND, "metadata"),
        (None, None, SHADOW_CHECKPOINT_KIND, "kind"),
    ],
)
def test_invalid_source_fails_before_publication(
    tmp_path,
    expected_hash,
    metadata_override,
    checkpoint_kind,
    message,
):
    items_path = tmp_path / "items.json"
    source_path = tmp_path / "production.pth"
    output_dir = tmp_path / "shadow"
    _write_items(items_path)
    _write_production_checkpoint(
        source_path,
        items_path,
        metadata_override=metadata_override,
        checkpoint_kind=checkpoint_kind,
    )

    with pytest.raises(ValueError, match=message):
        publish_production_shadow(
            output_dir,
            production_checkpoint=source_path,
            expected_checkpoint_sha256=expected_hash or sha256_file(source_path),
            items_json=items_path,
            expected_items_sha256=sha256_file(items_path),
            source_commit="b" * 40,
            probe_count=4,
        )

    assert not output_dir.exists()


def test_equivalence_detects_parameter_change(tmp_path):
    items_path, source_path, _ = _fixture(tmp_path)
    mapper = build_id_mapper(str(items_path))
    source = load_production_checkpoint(
        source_path,
        expected_sha256=sha256_file(source_path),
        id_mapper=mapper,
    )
    changed = copy.deepcopy(source["state_dict"])
    first_key = next(iter(changed))
    changed[first_key].view(-1)[0] += 1.0

    evidence = prove_reload_equivalence(
        mapper,
        source["state_dict"],
        changed,
        probe_count=8,
    )

    assert evidence["passed"] is False
    assert evidence["parameter_sha256_match"] is False


def test_existing_output_is_never_replaced(tmp_path):
    items_path, source_path, _ = _fixture(tmp_path)
    output_dir = tmp_path / "shadow"
    output_dir.mkdir()
    marker = output_dir / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        publish_production_shadow(
            output_dir,
            production_checkpoint=source_path,
            expected_checkpoint_sha256=sha256_file(source_path),
            items_json=items_path,
            expected_items_sha256=sha256_file(items_path),
            source_commit="c" * 40,
            probe_count=4,
        )

    assert marker.read_text(encoding="utf-8") == "keep"


def test_bound_inputs_are_read_once(tmp_path, monkeypatch):
    items_path, source_path, _ = _fixture(tmp_path)
    output_dir = tmp_path / "shadow"
    bound_paths = {items_path.resolve(), source_path.resolve()}
    counts = {path: 0 for path in bound_paths}
    expected_source_hash = sha256_file(source_path)
    expected_items_hash = sha256_file(items_path)
    original_read_bytes = Path.read_bytes

    def counted_read_bytes(path):
        resolved = path.resolve()
        if resolved in counts:
            counts[resolved] += 1
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read_bytes)
    publish_production_shadow(
        output_dir,
        production_checkpoint=source_path,
        expected_checkpoint_sha256=expected_source_hash,
        items_json=items_path,
        expected_items_sha256=expected_items_hash,
        source_commit="d" * 40,
        probe_count=4,
    )

    assert counts == {path: 1 for path in bound_paths}


def test_preexisting_unique_staging_is_not_deleted(tmp_path, monkeypatch):
    items_path, source_path, _ = _fixture(tmp_path)
    output_dir = tmp_path / "shadow"
    monkeypatch.setattr(
        shadow_module.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex="fixed"),
    )
    staging = tmp_path / ".shadow.fixed.staging"
    staging.mkdir()
    marker = staging / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        publish_production_shadow(
            output_dir,
            production_checkpoint=source_path,
            expected_checkpoint_sha256=sha256_file(source_path),
            items_json=items_path,
            expected_items_sha256=sha256_file(items_path),
            source_commit="e" * 40,
            probe_count=4,
        )

    assert marker.read_text(encoding="utf-8") == "keep"
