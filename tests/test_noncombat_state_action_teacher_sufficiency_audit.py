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
            "blocked_attempt_failure": _binding("reports/blocked-failure.json"),
            "consumed_registration": _binding("reports/consumed-registration.json"),
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
            "synthetic_benchmark": _binding("reports/synthetic-benchmark.json"),
            "teacher_policy_id": "sts_lightspeed_simple_agent_target_v1",
            "train_dataset_sha256": _hash("c"),
            "train_input": _binding("reports/train.json.gz"),
            "train_input_manifest": _binding("reports/train-manifest.json"),
        },
        "recovery": audit._recovery_contract(),
        "schema_version": audit.REGISTRATION_SCHEMA_VERSION,
    }


def _consumed_registration() -> dict:
    return {
        "audit": audit._audit_contract(),
        "authority": {"historical": False},
        "identity": {"train_dataset_sha256": _hash("c")},
        "schema_version": audit.CONSUMED_REGISTRATION_SCHEMA_VERSION,
    }


def _blocked_failure(consumed: dict) -> dict:
    payload = audit.canonical_json_bytes(consumed)
    return {
        "attempt": {
            "registration_file": {
                "sha256": audit.sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        },
        "authority": {"historical": False},
        "failure": {
            "classification": "registered_audit_wall_time_exceeded",
            "registered_max_wall_seconds": 120.0,
            "stage": "post_analysis_pre_publication",
        },
        "isolation": {
            "canonical_artifact_count": 0,
            "canonical_output_root_absent": True,
        },
        "resolution": {
            "same_registration_retry_allowed": False,
            "threshold_change_allowed": False,
            "verdict": "blocked",
        },
        "schema_version": audit.BLOCKED_FAILURE_SCHEMA_VERSION,
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


def _bind_policy_views(row: dict) -> dict:
    value = copy.deepcopy(row)
    state = value["source_snapshot"]["state"]
    value["policy_views"] = []
    for candidate in value["candidate_actions"]:
        view = audit.project_policy_view(state, candidate)
        value["policy_views"].append(
            {
                "action_id": candidate["action_id"],
                "policy_view": view,
                "sha256": audit.sha256_bytes(audit.canonical_json_bytes(view)),
            }
        )
    return value


def _representation_rows() -> tuple[dict, dict]:
    route = audit._synthetic_route_row(7)
    for x, candidate in enumerate(route["candidate_actions"]):
        candidate["action_id"] = f"route:map_node:{x}:0"
    route["teacher"]["action_id"] = audit.reconstruct_route_action(
        route["source_snapshot"]["state"], route["candidate_actions"], _source_facts()
    )
    route = _bind_policy_views(route)

    card = audit._synthetic_card_reward_row(9)
    first = card["candidate_actions"][0]
    second = card["candidate_actions"][1]
    second["raw"] = copy.deepcopy(first["raw"])
    second["raw"]["slot"] = 1
    card["source_snapshot"]["state"]["baseline_history"] = ["synthetic-leakage"]
    card["teacher"]["action_id"] = audit.reconstruct_card_reward_action(
        card["candidate_actions"], _source_facts()
    )
    card = _bind_policy_views(card)
    return route, card


def _validated_context(
    *, registration: dict | None = None, train_input: dict | None = None
) -> audit.ValidatedAuditContext:
    registration = copy.deepcopy(registration or _registration())
    train_input = copy.deepcopy(
        train_input
        or {
            "dataset": {"rows": []},
            "schema_version": "fixture",
            "source": {"train_dataset_sha256": _hash("c")},
        }
    )
    return audit.ValidatedAuditContext(
        registration=registration,
        train_input=train_input,
        source_facts=_source_facts(),
        identity_summary={},
        registration_sha256=audit.sha256_bytes(
            audit.canonical_json_bytes(registration)
        ),
        train_dataset_sha256=_hash("c"),
        _seal=audit._CONTEXT_SEAL,
    )


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

    wall_time_drift = copy.deepcopy(registration)
    wall_time_drift["audit"]["limits"]["max_wall_seconds"] = 121.0
    with pytest.raises(audit.AuditBlocked, match="contract"):
        audit.validate_registration(wall_time_drift)

    signature_drift = copy.deepcopy(registration)
    signature_drift["audit"]["signatures"]["structured-hash-2048-v1"][
        "hash_dim"
    ] = 4096
    with pytest.raises(audit.AuditBlocked, match="contract"):
        audit.validate_registration(signature_drift)

    recovery_drift = copy.deepcopy(registration)
    recovery_drift["recovery"]["context_mode"] = "retry-v1"
    with pytest.raises(audit.AuditBlocked, match="recovery contract"):
        audit.validate_registration(recovery_drift)


def test_registration_v2_rejects_v1_retry_and_blocked_lineage_drift():
    legacy = copy.deepcopy(_registration())
    legacy["schema_version"] = audit.CONSUMED_REGISTRATION_SCHEMA_VERSION
    with pytest.raises(audit.AuditBlocked, match="schema"):
        audit.validate_registration(legacy)

    consumed = _consumed_registration()
    failure = _blocked_failure(consumed)
    assert audit.validate_blocked_lineage(
        consumed_registration=consumed, failure=failure
    )["same_registration_retry_allowed"] is False

    changed_failure = copy.deepcopy(failure)
    changed_failure["failure"]["registered_max_wall_seconds"] = 121.0
    with pytest.raises(audit.AuditBlocked, match="wall-time"):
        audit.validate_blocked_lineage(
            consumed_registration=consumed, failure=changed_failure
        )

    changed_registration = copy.deepcopy(consumed)
    changed_registration["audit"]["limits"]["max_wall_seconds"] = 121.0
    changed_failure = _blocked_failure(changed_registration)
    with pytest.raises(audit.AuditBlocked, match="contract drifted"):
        audit.validate_blocked_lineage(
            consumed_registration=changed_registration, failure=changed_failure
        )


def test_validated_context_loader_is_single_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
):
    registration = _registration()
    train_input = {
        "dataset": {"rows": []},
        "schema_version": "fixture",
        "source": {"train_dataset_sha256": _hash("c")},
    }
    calls = {"identity": 0, "registration": 0, "source": 0}

    def validate_registration(value: object) -> dict:
        calls["registration"] += 1
        assert value is registration
        return registration

    def validate_identity(value: object, *, repo_root: Path, return_train_input: bool):
        calls["identity"] += 1
        assert value is registration
        assert return_train_input is True
        return {"identity": "validated", "train_input": train_input}

    def load_source(value: object, *, repo_root: Path) -> dict:
        calls["source"] += 1
        assert value is registration
        return _source_facts()

    monkeypatch.setattr(audit, "validate_registration", validate_registration)
    monkeypatch.setattr(audit, "validate_registered_identity", validate_identity)
    monkeypatch.setattr(audit, "load_source_facts", load_source)
    context = audit.load_validated_audit_context(registration, repo_root=Path("repo"))
    assert calls == {"identity": 1, "registration": 1, "source": 1}
    assert context.train_input is train_input
    assert context.identity_summary == {"identity": "validated"}


def test_validated_context_rejects_raw_stale_and_cross_registration_values():
    assert audit._validate_audit_context(_validated_context()).train_dataset_sha256 == _hash(
        "c"
    )
    with pytest.raises(audit.AuditBlocked, match="registered validated context"):
        audit._validate_audit_context({})

    stale_registration = _validated_context()
    stale_registration.registration["authority"]["model_fitting"] = True
    with pytest.raises(audit.AuditBlocked, match="registration identity drifted"):
        audit._validate_audit_context(stale_registration)

    stale_dataset = _validated_context()
    stale_dataset.train_input["source"]["train_dataset_sha256"] = _hash("d")
    with pytest.raises(audit.AuditBlocked, match="train identity drifted"):
        audit._validate_audit_context(stale_dataset)

    other_registration = _registration()
    other_registration["identity"]["train_dataset_sha256"] = _hash("d")
    cross_registration = _validated_context(registration=other_registration)
    with pytest.raises(audit.AuditBlocked, match="crosses registrations"):
        audit._validate_audit_context(cross_registration)

    stale_source = _validated_context()
    stale_source.source_facts["schema_version"] = "stale"
    with pytest.raises(audit.AuditBlocked, match="source facts"):
        audit._validate_audit_context(stale_source)


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


def test_optimized_representations_match_reference_maps_vectors_and_artifacts():
    route, card = _representation_rows()
    facts = _source_facts()
    for row in (route, card):
        state = row["source_snapshot"]["state"]
        candidates = row["candidate_actions"]
        optimized_maps = audit.optimized_structured_feature_maps(
            state, candidates, category=row["category"]
        )
        reference_maps = [
            audit.structured_feature_map(state, candidate, category=row["category"])
            for candidate in candidates
        ]
        assert optimized_maps == reference_maps
        assert audit.build_representation_row_optimized(row, facts) == (
            audit.build_representation_row(row, facts)
        )

    registration = audit.validate_registration(_registration())
    train_input = {
        "dataset": {"rows": [route, card]},
        "source": {"train_dataset_sha256": _hash("c")},
    }
    reference = audit._execute_audit_rows(
        registration=registration,
        normalized_input=train_input,
        source_facts=facts,
        optimized=False,
    )
    optimized = audit._execute_audit_rows(
        registration=registration,
        normalized_input=train_input,
        source_facts=facts,
        optimized=True,
    )
    assert optimized == reference
    assert audit.build_artifacts(
        registration=registration, execution=optimized
    ) == audit.build_artifacts(registration=registration, execution=reference)


def test_optimized_representation_fails_closed_on_policy_view_and_cache_drift():
    route, card = _representation_rows()
    facts = _source_facts()

    missing = copy.deepcopy(card)
    missing.pop("policy_views")
    with pytest.raises(audit.AuditBlocked, match="inventory"):
        audit.build_representation_row_optimized(missing, facts)

    reordered = copy.deepcopy(card)
    reordered["policy_views"].reverse()
    with pytest.raises(audit.AuditBlocked, match="identity"):
        audit.build_representation_row_optimized(reordered, facts)

    tampered = copy.deepcopy(card)
    tampered["policy_views"][0]["policy_view"]["state"]["gold"] = 9999
    with pytest.raises(audit.AuditBlocked, match="payload"):
        audit.build_representation_row_optimized(tampered, facts)

    invalid_hash = copy.deepcopy(card)
    invalid_hash["policy_views"][0]["sha256"] = "not-a-hash"
    with pytest.raises(audit.AuditBlocked, match="identity"):
        audit.build_representation_row_optimized(
            invalid_hash, facts, policy_view_payloads_already_validated=True
        )

    nonfinite = copy.deepcopy(card)
    nonfinite["source_snapshot"]["state"]["cur_hp"] = float("nan")
    with pytest.raises(audit.AuditBlocked, match="finite"):
        audit.optimized_structured_feature_maps(
            nonfinite["source_snapshot"]["state"],
            nonfinite["candidate_actions"],
            category="card_reward",
        )

    other_route = audit._synthetic_route_row(8)
    first_maps = audit.optimized_structured_feature_maps(
        route["source_snapshot"]["state"],
        route["candidate_actions"],
        category="route",
    )
    second_maps = audit.optimized_structured_feature_maps(
        other_route["source_snapshot"]["state"],
        other_route["candidate_actions"],
        category="route",
    )
    assert first_maps != second_maps


def test_synthetic_performance_workload_has_exact_counts_and_no_corpus_identity():
    workload = audit.build_synthetic_performance_workload()
    assert len(workload) == 602
    assert sum(row["category"] == "route" for row in workload) == 300
    assert sum(row["category"] == "card_reward" for row in workload) == 302
    assert all(len(row["candidate_actions"]) > 1 for row in workload)
    assert all(row["seed"] not in audit.REGISTERED_TRAIN_SEEDS for row in workload)
    fixture_text = audit.canonical_json_bytes(workload).decode("utf-8")
    assert "noncombat_structured_baseline_train_input" not in fixture_text
    assert "reports/" not in fixture_text


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
