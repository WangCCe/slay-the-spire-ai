import copy
import json
from pathlib import Path

import pytest
import torch

from analysis_scripts.combat_lightspeed_checkpoint_interpolation import (
    interpolate_state,
    publish_interpolations,
    validate_alphas,
)
from analysis_scripts.combat_lightspeed_frozen_candidate_comparison import (
    CandidateBinding,
    ComparisonBlocked,
    load_candidate,
)
from analysis_scripts.combat_lightspeed_training_smoke import (
    create_fresh_trainer,
    parameter_sha256,
)
from analysis_scripts.combat_lightspeed_bridge import sha256_file
from spirecomm.ai.rl.checkpoint_io import save_torch_checkpoint
from spirecomm.ai.rl.v2.id_mapping import IdMapper


def _mapper():
    return IdMapper(
        card_ids={"Strike": 1},
        potion_ids={"Fire Potion": 1},
        relic_ids={"Burning Blood": 1},
        card_tags={"Strike": []},
    )


def _write_candidate(path: Path, state_dict, *, production_compatible=False):
    save_torch_checkpoint(
        {
            "checkpoint_schema_version": 0,
            "checkpoint_kind": "simulator_training_smoke",
            "source_type": "sts_lightspeed_combat_simulation",
            "production_compatible": production_compatible,
            "online_network_state_dict": copy.deepcopy(state_dict),
            "metadata": {
                "authority": {"simulator_fitting": True, "promotion": False},
                "source_binding": {
                    "candidate_parameter_sha256": parameter_sha256(state_dict)
                },
            },
        },
        str(path),
    )


def test_interpolation_is_exact_and_preserves_dtype():
    parent = {"weight": torch.tensor([1.0, 3.0], dtype=torch.float32)}
    candidate = {"weight": torch.tensor([5.0, -1.0], dtype=torch.float32)}

    result = interpolate_state(parent, candidate, 0.25)

    assert result["weight"].dtype == torch.float32
    assert torch.equal(
        result["weight"],
        parent["weight"] + 0.25 * (candidate["weight"] - parent["weight"]),
    )


@pytest.mark.parametrize("alphas", [(), (0.0,), (1.0,), (-0.1,), (0.5, 0.5), (float("nan"),)])
def test_alpha_validation_rejects_invalid_complete_request(alphas):
    with pytest.raises(ValueError, match="alpha"):
        validate_alphas(alphas)


def test_interpolation_rejects_nonfloating_or_incompatible_state():
    with pytest.raises(ValueError, match="floating"):
        interpolate_state(
            {"value": torch.tensor([1], dtype=torch.int64)},
            {"value": torch.tensor([2], dtype=torch.int64)},
            0.5,
        )
    with pytest.raises(ValueError, match="structure"):
        interpolate_state(
            {"left": torch.tensor([1.0])},
            {"right": torch.tensor([2.0])},
            0.5,
        )


def test_publication_is_bound_deterministic_and_comparator_compatible(tmp_path):
    trainer = create_fresh_trainer(_mapper(), seed=61, batch_size=2, learning_starts=2)
    parent_state = copy.deepcopy(trainer.online_network.state_dict())
    candidate_state = {
        key: value + torch.full_like(value, 0.25)
        for key, value in parent_state.items()
    }
    parent_path = tmp_path / "parent.pth"
    candidate_path = tmp_path / "candidate.pth"
    _write_candidate(parent_path, parent_state)
    _write_candidate(candidate_path, candidate_state)
    output_dir = tmp_path / "interpolations"

    report = publish_interpolations(
        output_dir,
        parent_binding=CandidateBinding("parent", parent_path, sha256_file(parent_path)),
        candidate_binding=CandidateBinding(
            "candidate", candidate_path, sha256_file(candidate_path)
        ),
        alphas=(0.25, 0.5, 0.75),
        source_commit="a" * 40,
    )

    assert report["verdict"] == "interpolations_ready"
    assert [row["alpha"] for row in report["outputs"]] == [0.25, 0.5, 0.75]
    for row in report["outputs"]:
        path = output_dir / row["path"]
        loaded = load_candidate(
            CandidateBinding(f"alpha-{row['alpha']}", path, row["sha256"])
        )
        expected = interpolate_state(parent_state, candidate_state, row["alpha"])
        assert parameter_sha256(loaded["state_dict"]) == parameter_sha256(expected)
        assert loaded["source_binding"]["parent_checkpoint_sha256"] == sha256_file(
            parent_path
        )
        assert loaded["source_binding"]["candidate_checkpoint_sha256"] == sha256_file(
            candidate_path
        )
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["artifacts"]) == {
        "report.json",
        "simulator_only_candidate_alpha_0p25.pth",
        "simulator_only_candidate_alpha_0p5.pth",
        "simulator_only_candidate_alpha_0p75.pth",
    }


def test_invalid_bound_input_creates_no_output(tmp_path):
    trainer = create_fresh_trainer(_mapper(), seed=67, batch_size=2, learning_starts=2)
    parent_path = tmp_path / "parent.pth"
    candidate_path = tmp_path / "candidate.pth"
    _write_candidate(parent_path, trainer.online_network.state_dict())
    _write_candidate(
        candidate_path,
        trainer.online_network.state_dict(),
        production_compatible=True,
    )
    output_dir = tmp_path / "interpolations"

    with pytest.raises(ComparisonBlocked, match="production_compatible"):
        publish_interpolations(
            output_dir,
            parent_binding=CandidateBinding("parent", parent_path, sha256_file(parent_path)),
            candidate_binding=CandidateBinding(
                "candidate", candidate_path, sha256_file(candidate_path)
            ),
            alphas=(0.5,),
            source_commit="b" * 40,
        )

    assert not output_dir.exists()
