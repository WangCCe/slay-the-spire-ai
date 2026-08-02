# Non-Combat State/Action and Teacher Sufficiency Audit

- Verdict: `simpleagent_unsuitable_as_policy_quality_gate`
- Next proposal class: `outcome-backed-noncombat-rl-readiness`
- Audited rows: 993
- Multi-candidate rows: 602
- Teacher reconstruction: 993/993 exact
- Raw adapter missing dependencies: 0

## Representation Evidence

| Signature | Repeated decision groups | Semantic conflicts | Non-equivalent aliases | Pairwise contradictions |
| --- | ---: | ---: | ---: | ---: |
| `teacher-source-v1` | 0 | 0 | 0 | 0 |
| `adapter-observable-v1` | 0 | 0 | 0 | 0 |
| `legacy-hash-1024-v1` | 0 | 0 | 0 | 0 |
| `structured-hash-2048-v1` | 0 | 0 | 0 | 0 |

## Teacher Suitability

- `route_replans_with_current_state`: FAIL (source_facts.route.replans_only_at_map_entry)
- `route_reads_survivability`: FAIL (source_facts.route.reads_current_hp)
- `route_reads_run_resources`: FAIL (source_facts.route.reads_current_gold)
- `card_copy_limit_uses_actual_deck`: FAIL (source_facts.card.reads_actual_deck)
- `card_reads_deck_and_run_context`: FAIL (source_facts.card.reads_actual_deck/read_run_context)
- `card_values_skip_vs_bowl`: FAIL (source_facts.card.values_singing_bowl)

## Boundary

This result measures deterministic source closure and representation aliases on the preserved train corpus. It does not authorize model fitting, native execution, gameplay, formal RL, qualification, or policy promotion.

Registered implementation: `d86d73f84f07b2106e961ca29346941d7158fb93`
