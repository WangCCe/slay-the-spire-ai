import copy
import hashlib
import json
from pathlib import Path

import pytest

from analysis_scripts.bottled_policy_oracle import BottledOracleResult
from analysis_scripts.noncombat_card_only_native_baseline_rl_pilot import (
    CORPUS_ARTIFACT_SCHEMA_VERSION,
    DATASET_SCHEMA_VERSION,
    DEMONSTRATION_SCHEMA_VERSION,
    BoundCardCorpus,
    CardOnlyPilotBlocked,
    label_bound_card_corpus,
    load_bound_card_corpus,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    canonical_json_bytes,
)


PROVENANCE = {
    "adapter_commit": "a" * 40,
    "adapter_source_sha256": "b" * 64,
    "build": {
        "adapter_api_version": ADAPTER_API_VERSION,
        "compiler": "test",
        "cpp_standard": "20",
        "python": "3.10",
    },
    "module_sha256": "c" * 64,
    "simulator_commit": "d" * 40,
    "simulator_source_sha256": "e" * 64,
    "submodules": {"json": "f" * 40, "pybind11": "1" * 40},
}


def _candidate(action_id, kind, label, raw):
    return {
        "action_id": action_id,
        "available": True,
        "category": "card_reward",
        "kind": kind,
        "label": label,
        "raw": raw,
    }


def _card_row(*, cohort="train", bowl=False, duplicate=False):
    cards = [
        {"id": "ANGER", "name": "Anger", "slot": 0, "upgrade_count": 0, "upgraded": False}
    ]
    if duplicate:
        cards.append(
            {"id": "ANGER", "name": "Anger", "slot": 1, "upgrade_count": 0, "upgraded": False}
        )
    candidates = [
        _candidate(
            f"take-{index}",
            "take",
            card["name"],
            {**card, "misc": 0, "reward_index": 0},
        )
        for index, card in enumerate(cards)
    ]
    candidates.append(
        _candidate(
            "bowl" if bowl else "skip",
            "bowl" if bowl else "skip",
            "gain 2 max hp" if bowl else "skip",
            {"reward_index": 0},
        )
    )
    snapshot = {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_control": {"history": [], "policy_id": NATIVE_TARGET_POLICY_ID},
        "category": "card_reward",
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "state": {
            "act": 1,
            "decision_context": {"cards": cards, "has_singing_bowl": bowl, "reward_index": 0},
            "deck": [
                {"id": "STRIKE_RED", "name": "Strike", "slot": 0, "upgrade_count": 0, "upgraded": False}
            ],
            "floor": 2,
        },
        "terminal": False,
    }
    return {
        "candidate_actions": candidates,
        "candidate_actions_sha256": hashlib.sha256(canonical_json_bytes(candidates)).hexdigest(),
        "category": "card_reward",
        "cohort": cohort,
        "decision_index": 0,
        "policy_views": [],
        "provenance": copy.deepcopy(PROVENANCE),
        "schema_version": DEMONSTRATION_SCHEMA_VERSION,
        "seed": 1000,
        "source_snapshot": snapshot,
        "source_snapshot_sha256": hashlib.sha256(canonical_json_bytes(snapshot)).hexdigest(),
        "source_type": SOURCE_TYPE,
        "successor": {"state": {}, "terminal": True},
        "teacher": {
            "action_id": "take-0",
            "category": "card_reward",
            "policy_id": NATIVE_TARGET_POLICY_ID,
            "schema_version": NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
        },
    }


def _write_corpus(path: Path, *, final_test=None, duplicate=False):
    datasets = {}
    for cohort in ("train", "validation"):
        row = _card_row(cohort=cohort, duplicate=duplicate)
        datasets[cohort] = {
            "all_categories": ["card_reward"],
            "cohort": cohort,
            "episodes": [],
            "row_count": 1,
            "rows": [row],
            "schema_version": DATASET_SCHEMA_VERSION,
            "seeds": [1000],
            "source_type": SOURCE_TYPE,
            "teacher_policy_id": NATIVE_TARGET_POLICY_ID,
        }
    datasets["final_test"] = final_test
    value = {
        "datasets": datasets,
        "registration_sha256": "2" * 64,
        "schema_version": CORPUS_ARTIFACT_SCHEMA_VERSION,
    }
    path.write_bytes(canonical_json_bytes(value))
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size


def _load_fixture(path, *, final_test=None, duplicate=False):
    sha256, size = _write_corpus(path, final_test=final_test, duplicate=duplicate)
    return load_bound_card_corpus(
        path,
        expected_sha256=sha256,
        expected_size_bytes=size,
        expected_registration_sha256="2" * 64,
        expected_card_row_counts={"train": 1, "validation": 1},
    )


class FakeOracle:
    def __init__(self, labels, *, dirty=False, commit="abc123"):
        self.labels = iter(labels)
        self.source = {
            "commit": commit,
            "dirty": dirty,
            "mode": "native_bottled",
            "path": "C:/bottled_ai",
            "strategy": "REQUESTED_STRIKE",
        }

    def source_metadata(self):
        return dict(self.source)

    def evaluate(self, sample):
        assert sample.category == "card_reward"
        assert sample.evidence_quality == "complete"
        assert sample.context["offered"]
        return BottledOracleResult(
            label=next(self.labels),
            confidence="high",
            reason="fixture",
            source=dict(self.source),
        )


def test_bound_reader_extracts_only_train_and_validation_card_rows(tmp_path):
    corpus = _load_fixture(tmp_path / "demonstrations.json")

    assert set(corpus.rows) == {"train", "validation"}
    assert [row["cohort"] for row in corpus.rows["train"]] == ["train"]
    assert corpus.source["sha256"]


@pytest.mark.parametrize("drift", ["size", "sha256"])
def test_bound_reader_rejects_corpus_drift(tmp_path, drift):
    path = tmp_path / "demonstrations.json"
    sha256, size = _write_corpus(path)

    with pytest.raises(CardOnlyPilotBlocked, match=drift):
        load_bound_card_corpus(
            path,
            expected_sha256="0" * 64 if drift == "sha256" else sha256,
            expected_size_bytes=size + 1 if drift == "size" else size,
            expected_registration_sha256="2" * 64,
            expected_card_row_counts={"train": 1, "validation": 1},
        )


def test_bound_reader_denies_final_test_request_before_reading(tmp_path):
    path = tmp_path / "missing.json"

    with pytest.raises(CardOnlyPilotBlocked, match="final_test"):
        load_bound_card_corpus(path, cohorts=("train", "final_test"))


def test_bound_reader_rejects_populated_final_test(tmp_path):
    path = tmp_path / "demonstrations.json"
    sha256, size = _write_corpus(path, final_test={"rows": ["protected"]})

    with pytest.raises(CardOnlyPilotBlocked, match="must remain absent"):
        load_bound_card_corpus(
            path,
            expected_sha256=sha256,
            expected_size_bytes=size,
            expected_registration_sha256="2" * 64,
            expected_card_row_counts={"train": 1, "validation": 1},
        )


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (("Anger", "skip"), {"skip": 1, "take": 1}),
    ],
)
def test_bottled_bridge_maps_take_and_skip_and_reports_disagreement(
    tmp_path, labels, expected
):
    corpus = _load_fixture(tmp_path / "demonstrations.json")

    result = label_bound_card_corpus(
        corpus, FakeOracle(labels), expected_bottled_commit="abc123"
    )

    assert result["counts"]["label_family"] == expected
    assert result["counts"]["simple_agent_agreement"] == {"agree": 1, "disagree": 1}
    assert result["rows"]["train"][0]["bottled_action_id"] == "take-0"
    assert result["rows"]["validation"][0]["bottled_action_id"] == "skip"


def test_bottled_bridge_maps_bowl(tmp_path):
    path = tmp_path / "demonstrations.json"
    sha256, size = _write_corpus(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    for cohort in ("train", "validation"):
        row = _card_row(cohort=cohort, bowl=True)
        value["datasets"][cohort]["rows"] = [row]
    path.write_bytes(canonical_json_bytes(value))
    corpus = load_bound_card_corpus(
        path,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        expected_size_bytes=path.stat().st_size,
        expected_registration_sha256="2" * 64,
        expected_card_row_counts={"train": 1, "validation": 1},
    )

    result = label_bound_card_corpus(
        corpus, FakeOracle(("bowl", "bowl")), expected_bottled_commit="abc123"
    )

    assert result["counts"]["label_family"] == {"bowl": 2}


def test_bottled_bridge_rejects_missing_context(tmp_path):
    corpus = _load_fixture(tmp_path / "demonstrations.json")
    bad_row = copy.deepcopy(corpus.rows["train"][0])
    del bad_row["source_snapshot"]["state"]["decision_context"]
    bad_row["source_snapshot_sha256"] = hashlib.sha256(
        canonical_json_bytes(bad_row["source_snapshot"])
    ).hexdigest()
    bad = BoundCardCorpus(corpus.source, {"train": (bad_row,)})

    with pytest.raises(CardOnlyPilotBlocked, match="decision_context"):
        label_bound_card_corpus(
            bad, FakeOracle(("skip",)), expected_bottled_commit="abc123"
        )


def test_bottled_bridge_rejects_ambiguous_card_label(tmp_path):
    corpus = _load_fixture(tmp_path / "demonstrations.json", duplicate=True)

    with pytest.raises(CardOnlyPilotBlocked, match="maps to 2"):
        label_bound_card_corpus(
            corpus, FakeOracle(("Anger", "Anger")), expected_bottled_commit="abc123"
        )


def test_bottled_bridge_requires_clean_bound_checkout(tmp_path):
    corpus = _load_fixture(tmp_path / "demonstrations.json")

    with pytest.raises(CardOnlyPilotBlocked, match="clean"):
        label_bound_card_corpus(
            corpus, FakeOracle((), dirty=True), expected_bottled_commit="abc123"
        )
    with pytest.raises(CardOnlyPilotBlocked, match="commit mismatch"):
        label_bound_card_corpus(
            corpus, FakeOracle((), commit="different"), expected_bottled_commit="abc123"
        )
