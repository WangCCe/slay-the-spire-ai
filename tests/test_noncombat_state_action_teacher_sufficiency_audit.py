from __future__ import annotations

import copy
from pathlib import Path

import pytest

from analysis_scripts import noncombat_state_action_teacher_sufficiency_audit as audit


def _hash(char: str = "a") -> str:
    return char * 64


def _binding(path: str) -> dict:
    return {"path": path, "sha256": _hash(), "size_bytes": 1}


def _registration() -> dict:
    return {
        "audit": audit._audit_contract(),
        "authority": audit._authority(),
        "identity": {
            "external_source": {
                "commit": "a" * 40,
                "files": [
                    {"path": path, "sha256": _hash(), "size_bytes": 1}
                    for path in audit.EXTERNAL_SOURCE_FILES
                ],
                "overall_dirty_at_registration": True,
                "overall_status_sha256": _hash(),
                "relevant_status": "",
                "repo_path": "D:\\source",
            },
            "implementation": {
                "commit": "b" * 40,
                "source_files": list(audit.REGISTERED_SOURCE_FILES),
                "source_sha256": _hash("b"),
            },
            "residual_failure_audit": _binding("reports/failure.md"),
            "residual_manifest": _binding("reports/artifact_manifest.json"),
            "residual_verdict": "poc_valid_without_route_card_residual",
            "runtime": {"python": "3.10.18", "torch": "2.5.1"},
            "teacher_policy_id": "sts_lightspeed_simple_agent_target_v1",
            "train_dataset_sha256": _hash("c"),
            "train_input": _binding("reports/train.json.gz"),
            "train_input_manifest": _binding("reports/train-manifest.json"),
        },
        "schema_version": audit.REGISTRATION_SCHEMA_VERSION,
    }


def _synthetic_source() -> tuple[str, str, str, str, str]:
    priorities = ",\n".join(f"CardId::CARD_{index}" for index in range(133))
    simple_cpp = f"""
static constexpr int mapWeights[3][6] = {{
    {{100,1000,100,10,1,0}},
    {{10,1000,10,100,1,0}},
    {{100,1000,100,1,10,0}},
}};

fixed_list<int,16> search::SimpleAgent::getBestMapPathForWeights(const Map &m, const int *weights) {{
    if (path.weight < curPath.weight + roomWeight) {{ path.weight = roomWeight; }}
    if (path.weight > bestPathWeight) {{ bestPathWeight = path.weight; }}
}}

void search::SimpleAgent::stepOutOfCombat(GameContext &gc) {{
    switch (gc.screenState) {{
        case ScreenState::MAP_SCREEN: {{
            if (gc.curMapNodeY < 0) {{
                mapPath = getBestMapPathForWeights(*gc.map, mapWeights[gc.act-1]);
            }}
            takeAction(gc, mapPath[gc.curMapNodeY+1]);
            break;
        }}
        case ScreenState::TREASURE_ROOM:
            break;
    }}
}}

void search::SimpleAgent::stepCardReward(GameContext &gc) {{
    const int lastRewardIdx = gc.info.rewardsContainer.cardRewardCount-1;
    auto lastCardReward = gc.info.rewardsContainer.cardRewards[lastRewardIdx];
    for (auto c : lastCardReward) {{ deckCounts[c.id] += 1; }}
    takeAction(gc, GameAction(GameAction::RewardsActionType::CARD, lastRewardIdx, 5) );
}}

constexpr std::array<CardId,133> cardsPriorities = {{
{priorities}
}};

void initMaps() {{
    maxCopies = new std::map<CardId, int>({{
        {{CardId::CARD_0, 1}},
        {{CardId::CARD_1, 2}}
    }});
}}
"""
    simple_h = "struct SimpleAgent { fixed_list<int,16> mapPath; };"
    card_cpp = """
bool Card::operator==(const Card &rhs) const {
    return id == rhs.id &&
           misc == rhs.misc &&
           upgraded == rhs.upgraded;
}
"""
    rooms_h = """
static constexpr const char* roomStrings[] = {
"SHOP", "REST", "EVENT", "ELITE", "MONSTER", "TREASURE",
"BOSS", "BOSS_TREASURE", "NONE", "INVALID"
};
"""
    adapter_cpp = """
std::vector<Candidate> cardRewardCandidates() const {
    skip.mode = Candidate::Mode::CARD_BOWL;
    skip.mode = Candidate::Mode::CARD_SKIP;
}
std::string probeNativeBaselineAction(sts::search::SimpleAgent *agentAfter) const {
    probe.baselineAgent_.stepCardReward(probe.gc_);
}
"""
    return simple_cpp, simple_h, card_cpp, rooms_h, adapter_cpp


def _route_state(*, favored_x: int | None = None, current_y: int = -1) -> dict:
    nodes = []
    for x in (0, 1):
        for y in range(15):
            room = "REST" if favored_x == x and y == 1 else "MONSTER"
            edges = [{"x": x, "y": y + 1}] if y < 14 else []
            nodes.append({"edges": edges, "room": room, "x": x, "y": y})
    return {
        "act": 1,
        "cur_map_node": {"x": -1 if current_y < 0 else favored_x or 0, "y": current_y},
        "map": {"burning_elite": {"buff": 0, "x": -1, "y": -1}, "nodes": nodes},
    }


def _route_candidates(y: int) -> list[dict]:
    return [
        {
            "action_id": f"route:map_node:{x}:{y}",
            "available": True,
            "category": "route",
            "kind": "map_node",
            "label": f"M@{x},{y}",
            "raw": {"room": "MONSTER", "x": x, "y": y},
        }
        for x in (0, 1)
    ]


def _card(
    slot: int,
    card_id: str,
    *,
    upgraded: bool = False,
    kind: str = "take",
) -> dict:
    if kind != "take":
        return {
            "action_id": f"card_reward:{kind}:0",
            "available": True,
            "category": "card_reward",
            "kind": kind,
            "label": kind,
            "raw": {"reward_index": 0},
        }
    return {
        "action_id": f"card_reward:take:0:{slot}:{card_id.lower()}",
        "available": True,
        "category": "card_reward",
        "kind": "take",
        "label": card_id,
        "raw": {
            "id": card_id,
            "misc": 0,
            "name": card_id,
            "reward_index": 0,
            "slot": slot,
            "upgrade_count": 1 if upgraded else 0,
            "upgraded": upgraded,
        },
    }


def _source_facts() -> dict:
    return {
        "blocks": {},
        "card": {
            "card_priority_count": 3,
            "card_priority_duplicate_count": 1,
            "card_priority_order": ["GOOD", "DUP", "DUP"],
            "equality_fields": ["id", "misc", "upgraded"],
            "copy_limit_count": 1,
            "copy_limits": {"LIMITED": 1},
            "default_priority": 0,
            "offer_count_used_for_copy_limit": True,
            "reads_actual_deck": False,
            "reads_run_context": False,
            "skip_action_index": 5,
            "values_singing_bowl": False,
        },
        "route": {
            "cached_path_member": "mapPath",
            "map_weights": [
                [100, 1000, 100, 10, 1, 0],
                [10, 1000, 10, 100, 1, 0],
                [100, 1000, 100, 1, 10, 0],
            ],
            "reads_current_gold": False,
            "reads_current_hp": False,
            "replans_only_at_map_entry": True,
            "strict_final_tie_keeps_first": True,
            "strict_path_tie_keeps_existing": True,
        },
        "schema_version": audit.SOURCE_FACTS_SCHEMA_VERSION,
    }


def _metric_row(
    row_id: str,
    *,
    target_index: int,
    signatures: dict[str, list[str]],
    semantics: list[list],
) -> dict:
    representations = {}
    for signature_id in audit.SIGNATURE_IDS:
        candidate_signatures = signatures[signature_id]
        representations[signature_id] = {
            "candidate_signatures": candidate_signatures,
            "decision_signature": audit.sha256_bytes(
                audit.canonical_json_bytes(
                    {
                        "candidate_signatures": candidate_signatures,
                        "category": "card_reward",
                    }
                )
            ),
        }
    return {
        "category": "card_reward",
        "representations": representations,
        "row_id": row_id,
        "semantic_action_keys": semantics,
        "target_index": target_index,
    }


def test_registration_rejects_authority_and_contract_drift():
    registration = _registration()
    assert audit.validate_registration(registration)["audit"] == audit._audit_contract()

    authority_drift = copy.deepcopy(registration)
    authority_drift["authority"]["model_fitting"] = True
    with pytest.raises(audit.AuditBlocked, match="authority"):
        audit.validate_registration(authority_drift)

    contract_drift = copy.deepcopy(registration)
    contract_drift["audit"]["limits"]["max_model_fits"] = 1
    with pytest.raises(audit.AuditBlocked, match="contract"):
        audit.validate_registration(contract_drift)


def test_external_physical_identity_rejects_relevant_file_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    for relative in audit.EXTERNAL_SOURCE_FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")

    def fake_git(_root: Path, *args: str) -> str:
        return "a" * 40 if args[:2] == ("rev-parse", "HEAD") else ""

    monkeypatch.setattr(audit, "_git_output", fake_git)
    identity = audit._external_identity(tmp_path)
    assert audit.validate_external_identity(identity)["commit"] == "a" * 40

    (tmp_path / audit.EXTERNAL_SOURCE_FILES[-1]).write_text("changed", encoding="utf-8")
    with pytest.raises(audit.AuditBlocked, match="physical source"):
        audit.validate_external_identity(identity)


def test_source_parser_extracts_fixed_tables_and_rejects_anchor_drift():
    simple_cpp, simple_h, card_cpp, rooms_h, adapter_cpp = _synthetic_source()
    facts = audit.parse_source_facts(
        simple_agent_cpp=simple_cpp,
        simple_agent_h=simple_h,
        card_cpp=card_cpp,
        rooms_h=rooms_h,
        adapter_cpp=adapter_cpp,
    )
    assert facts["route"]["map_weights"][1] == [10, 1000, 10, 100, 1, 0]
    assert facts["card"]["card_priority_count"] == 133
    assert facts["card"]["copy_limits"] == {"CARD_0": 1, "CARD_1": 2}
    assert facts["card"]["reads_actual_deck"] is False

    with pytest.raises(audit.AuditBlocked, match="anchor"):
        audit.parse_source_facts(
            simple_agent_cpp=simple_cpp.replace(audit.CARD_FUNCTION_ANCHOR, "missing"),
            simple_agent_h=simple_h,
            card_cpp=card_cpp,
            rooms_h=rooms_h,
            adapter_cpp=adapter_cpp,
        )


def test_route_reconstruction_preserves_source_ties_and_cached_path_index():
    facts = _source_facts()
    assert audit.reconstruct_route_action(
        _route_state(), _route_candidates(0), facts
    ) == "route:map_node:0:0"
    assert audit.reconstruct_route_action(
        _route_state(favored_x=1), _route_candidates(0), facts
    ) == "route:map_node:1:0"
    assert audit.reconstruct_route_action(
        _route_state(favored_x=1, current_y=5), _route_candidates(6), facts
    ) == "route:map_node:1:6"


def test_card_reconstruction_uses_offer_counts_defaults_and_first_equal_card():
    facts = _source_facts()
    candidates = [_card(0, "LIMITED"), _card(1, "GOOD"), _card(2, "UNKNOWN")]
    assert audit.reconstruct_card_reward_action(candidates, facts) == candidates[2][
        "action_id"
    ]

    duplicate = [_card(0, "GOOD"), _card(1, "GOOD"), _card(2, "DUP")]
    assert audit.reconstruct_card_reward_action(duplicate, facts) == duplicate[0][
        "action_id"
    ]

    bowl = [_card(0, "LIMITED"), _card(1, "BOWL", kind="bowl")]
    assert audit.reconstruct_card_reward_action(bowl, facts) == bowl[1]["action_id"]


def test_semantic_action_key_collapses_only_equivalent_card_slots():
    first = _card(0, "GOOD", upgraded=True)
    second = _card(1, "GOOD", upgraded=True)
    different = _card(2, "GOOD", upgraded=False)
    assert audit.semantic_action_key("card_reward", first) == audit.semantic_action_key(
        "card_reward", second
    )
    assert audit.semantic_action_key(
        "card_reward", first
    ) != audit.semantic_action_key("card_reward", different)


def test_representation_metrics_isolate_projection_conflicts_and_aliases():
    base_one = {
        "teacher-source-v1": ["s1", "s2"],
        "adapter-observable-v1": ["a1", "a2"],
        "legacy-hash-1024-v1": ["l1", "l2"],
        "structured-hash-2048-v1": ["x", "x"],
    }
    base_two = {
        "teacher-source-v1": ["s3", "s4"],
        "adapter-observable-v1": ["a3", "a4"],
        "legacy-hash-1024-v1": ["l1", "l2"],
        "structured-hash-2048-v1": ["y1", "y2"],
    }
    rows = [
        _metric_row(
            "1:0",
            target_index=0,
            signatures=base_one,
            semantics=[["take", "A"], ["take", "B"]],
        ),
        _metric_row(
            "2:0",
            target_index=1,
            signatures=base_two,
            semantics=[["take", "A"], ["take", "B"]],
        ),
    ]
    metrics = audit.build_representation_metrics(rows)
    adapter = metrics["by_signature"]["adapter-observable-v1"]["all"]
    legacy = metrics["by_signature"]["legacy-hash-1024-v1"]["all"]
    structured = metrics["by_signature"]["structured-hash-2048-v1"]["all"]
    assert adapter["pairwise_contradiction_count"] == 0
    assert adapter["conflicting_semantic_target_group_count"] == 0
    assert legacy["pairwise_contradiction_count"] == 1
    assert legacy["conflicting_semantic_target_group_count"] == 1
    assert structured["non_equivalent_candidate_alias_row_count"] == 1
    assert structured["target_candidate_alias_row_count"] == 1


def test_real_feature_signatures_are_deterministic_without_model_fitting():
    offered = [_card(0, "GOOD"), _card(1, "UNKNOWN")]
    state = {
        "act": 1,
        "ascension": 0,
        "blue_key": False,
        "boss": "THE_GUARDIAN",
        "cur_hp": 70,
        "cur_map_node": {"x": 0, "y": 1},
        "cur_room": "MONSTER",
        "decision_context": {"cards": [item["raw"] for item in offered], "has_singing_bowl": False},
        "deck": [],
        "encounter": "CULTIST",
        "floor": 2,
        "gold": 99,
        "green_key": False,
        "map": None,
        "max_hp": 80,
        "outcome": "undecided",
        "potions": [],
        "red_key": False,
        "relics": [],
        "screen_state": "REWARDS",
        "seed": "4000",
    }
    row = {
        "candidate_actions": offered,
        "category": "card_reward",
        "decision_index": 1,
        "seed": 4000,
        "source_snapshot": {"state": state},
        "teacher": {"action_id": offered[0]["action_id"]},
    }
    first = audit.build_representation_row(row, _source_facts())
    second = audit.build_representation_row(row, _source_facts())
    assert first == second
    assert set(first["representations"]) == set(audit.SIGNATURE_IDS)

    torch = __import__("torch")
    with pytest.raises(audit.AuditBlocked, match="non-finite"):
        audit._tensor_row_hashes(torch.tensor([[float("nan")]]), expected_width=1)


def test_dependency_and_suitability_classify_teacher_limit_not_adapter_gap():
    facts = _source_facts()
    dependency = audit.build_dependency_coverage(facts)
    suitability = audit.build_teacher_suitability(facts)
    assert dependency["raw_adapter_actionable_gap_count"] == 0
    assert dependency["summary"]["structured_projection"][
        "missing_dependency_ids"
    ] == [
        "route.map_topology_and_rooms",
        "route.cached_map_path",
        "card.offer_order",
    ]
    assert len(suitability["critical_failed_check_ids"]) == 6
    assert (
        audit.classify_verdict(
            blockers=[],
            adapter_gap_reasons=[],
            suitability_failures=suitability["critical_failed_check_ids"],
        )
        == "simpleagent_unsuitable_as_policy_quality_gate"
    )
    assert (
        audit.classify_verdict(
            blockers=[],
            adapter_gap_reasons=["missing"],
            suitability_failures=suitability["critical_failed_check_ids"],
        )
        == "adapter_representation_repair_required"
    )
    assert (
        audit.classify_verdict(
            blockers=["source"],
            adapter_gap_reasons=["missing"],
            suitability_failures=[],
        )
        == "blocked"
    )


def test_hash_closed_artifacts_detect_tampering(tmp_path: Path):
    semantics = [["take", "A"], ["take", "B"]]
    signatures = {
        signature_id: [f"{signature_id}-a", f"{signature_id}-b"]
        for signature_id in audit.SIGNATURE_IDS
    }
    metrics = audit.build_representation_metrics(
        [_metric_row("1:0", target_index=0, signatures=signatures, semantics=semantics)]
    )
    suitability = audit.build_teacher_suitability(_source_facts())
    execution = {
        "dependency_coverage": audit.build_dependency_coverage(_source_facts()),
        "metrics": metrics,
        "report": {
            "adapter_gap_reasons": [],
            "audited_category_counts": {"card_reward": 1, "route": 0},
            "audited_row_count": 1,
            "authority": audit._authority(),
            "blockers": [],
            "max_candidate_count": 2,
            "multi_candidate_row_count": 1,
            "next_proposal_class": "outcome-backed-noncombat-rl-readiness",
            "reconstruction_match_count": 1,
            "reconstruction_mismatch_count": 0,
            "reconstruction_mismatch_examples": [],
            "schema_version": audit.REPORT_SCHEMA_VERSION,
            "singleton_counts": {"card_reward": 0, "route": 0},
            "suitability_failed_check_ids": suitability[
                "critical_failed_check_ids"
            ],
            "verdict": "simpleagent_unsuitable_as_policy_quality_gate",
        },
        "row_evidence": {"rows": [], "schema_version": audit.ROW_EVIDENCE_SCHEMA_VERSION},
        "source_facts": _source_facts(),
        "suitability": suitability,
    }
    artifacts = audit.build_artifacts(
        registration=_registration(), execution=execution
    )
    output = tmp_path / "audit"
    audit.publish_artifacts(output, artifacts)
    assert audit.validate_artifact_directory(output)["verdict"] == execution[
        "report"
    ]["verdict"]
    (output / "report.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(audit.AuditBlocked, match="hash closure"):
        audit.validate_artifact_directory(output)
