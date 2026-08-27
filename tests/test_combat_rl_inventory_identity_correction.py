import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest

from analysis_scripts.combat_lightspeed_replay_distribution_calibration import TransitionBatch
from analysis_scripts.combat_rl_inventory_identity_correction import (
    REPORT_SCHEMA_VERSION,
    audit_source,
    build_report,
    load_trace_rows,
    publish_report,
)
from spirecomm.ai.rl.v2.id_mapping import IdMapper
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2


ACTION_DIM = 133


def _batch():
    continuous = np.zeros((2, StateEncoderV2.CONTINUOUS_DIM), dtype=np.float32)
    continuous[:, 3] = np.asarray([1, 6], dtype=np.float32) / 50.0
    actions = np.asarray([0, 60], dtype=np.int64)
    masks = np.zeros((2, ACTION_DIM), dtype=bool)
    masks[np.arange(2), actions] = True
    return TransitionBatch(
        continuous=continuous,
        card_ids=np.zeros((2, 10), dtype=np.int64),
        potion_ids=np.zeros((2, 5), dtype=np.int64),
        relic_ids=np.zeros((2, 40), dtype=np.int64),
        actions=actions,
        rewards=np.zeros(2, dtype=np.float64),
        dones=np.zeros(2, dtype=bool),
        action_masks=masks,
    )


def _rows():
    return [
        {
            "action": {"type": "PlayCardAction"},
            "floor": 1,
            "in_combat": True,
            "potions": [
                {"id": "FairyPotion", "name": "Fairy in a Bottle"},
                {"id": "Potion Slot", "name": "Potion Slot"},
            ],
            "relics": [
                {"id": "Self Forming Clay", "name": "Self-Forming Clay"}
            ],
        },
        {
            "action": {"type": "PotionAction"},
            "floor": 6,
            "in_combat": True,
            "potions": [{"id": "UnknownPotion", "name": "Unknown Potion"}],
            "relics": [{"id": "Known Relic", "name": "Different Name"}],
        },
    ]


def _mapper():
    return IdMapper(
        card_ids={},
        potion_ids={"Fairy in a Bottle": 20},
        relic_ids={"Self-Forming Clay": 134, "Known Relic": 9},
        card_tags={},
    )


def _calibration():
    def metric(mean):
        return {"count": 1, "maximum": mean, "mean": mean, "minimum": mean, "standard_deviation": 0.0}

    real_strata = {
        "floor_00_05": {"semantic": {"potion_occupied_slots": metric(0.0), "relic_occupied_slots": metric(0.0)}},
        "floor_06_10": {"semantic": {"potion_occupied_slots": metric(0.0), "relic_occupied_slots": metric(0.0)}},
    }
    simulator_strata = {
        "floor_00_05": {"semantic": {"potion_occupied_slots": metric(1.0), "relic_occupied_slots": metric(1.0)}},
        "floor_06_10": {"semantic": {"potion_occupied_slots": metric(0.5), "relic_occupied_slots": metric(2.0)}},
    }
    return {
        "real": {"summary": {"strata": real_strata}},
        "simulator": {"summary": {"strata": simulator_strata}},
    }


def test_exact_join_recovers_name_fallback_and_preserves_known_precedence():
    audit = audit_source("test", _batch(), _rows(), _mapper())

    assert audit.report["transition_count"] == 2
    assert audit.report["inventory"]["potion"]["encoded_zero_recovered_occurrences"] == 1
    assert audit.report["inventory"]["potion"]["unresolved_occupied_occurrences"] == 1
    assert audit.report["inventory"]["relic"]["encoded_zero_recovered_occurrences"] == 2
    assert audit.report["inventory"]["relic"]["unresolved_occupied_occurrences"] == 0
    assert audit.report["resolution_counts"]["potion_display_name_fallback"] == 1
    assert audit.report["resolution_counts"]["potion_unresolved"] == 1
    assert audit.report["resolution_counts"]["relic_preferred_id"] == 1


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda rows: rows.pop(), "count mismatch"),
        (lambda rows: rows[0].update(floor=2), "floor mismatch"),
        (lambda rows: rows[0]["action"].update(type="EndTurnAction"), "action-family mismatch"),
    ],
)
def test_trace_replay_misalignment_fails_closed(mutation, match):
    rows = _rows()
    mutation(rows)

    with pytest.raises(ValueError, match=match):
        audit_source("test", _batch(), rows, _mapper())


def test_report_corrects_calibration_without_granting_authority():
    audit = audit_source("test", _batch(), _rows(), _mapper())

    report = build_report(
        {"test": audit},
        source_bindings=[{"label": "test"}],
        items_binding={"sha256": "a" * 64},
        calibration_binding={"sha256": "b" * 64},
        calibration_report=_calibration(),
    )

    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    assert report["verdict"] == "inventory_identity_correction_incomplete"
    assert not any(report["authority"].values())
    assert report["correction"]["aggregate"]["potion"]["recovered_occupied_occurrences"] == 1
    assert report["correction"]["strata"]["floor_00_05"]["inventory"]["potion"]["corrected_real"]["mean"] == 1.0


def test_trace_archive_hash_and_member_are_bound(tmp_path):
    archive = tmp_path / "trace.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(
            "ai_decision_trace_clean.jsonl",
            "\n".join(json.dumps(row) for row in _rows()),
        )
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    rows, evidence = load_trace_rows(archive, digest, label="test")

    assert len(rows) == 2
    assert evidence["filtered_transition_count"] == 2
    with pytest.raises(ValueError, match="hash mismatch"):
        load_trace_rows(archive, "0" * 64, label="test")


def test_publication_is_atomic_deterministic_and_does_not_touch_inputs(tmp_path):
    audit = audit_source("test", _batch(), _rows(), _mapper())
    report = build_report(
        {"test": audit},
        source_bindings=[{"label": "test"}],
        items_binding={"sha256": "a" * 64},
        calibration_binding={"sha256": "b" * 64},
        calibration_report=_calibration(),
    )
    source = tmp_path / "source.bin"
    source.write_bytes(b"immutable")
    output = tmp_path / "report"

    manifest = publish_report(output, report, max_report_bytes=1_000_000)

    assert source.read_bytes() == b"immutable"
    assert json.loads((output / "report.json").read_text()) == report
    assert manifest["artifacts"]["report.json"]["sha256"] == hashlib.sha256(
        (output / "report.json").read_bytes()
    ).hexdigest()
    with pytest.raises(ValueError, match="must be absent"):
        publish_report(output, report, max_report_bytes=1_000_000)
