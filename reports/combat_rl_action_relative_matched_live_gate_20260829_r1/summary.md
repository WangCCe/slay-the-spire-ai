# Action-relative matched live gate

**Decision:** `retain_production_r16_and_close_this_candidate_cohort`

The frozen candidate completed all 10 matched Ironclad A0 seeds with 73 safe takeovers and no runtime, legality, final-action, or restoration failures. It did not improve live progression: candidate won 0 floor pairs, parent won 2, and 8 tied; total floors were 219 vs 229, and Act 2 entries were 5 vs 6.

| Pair | Seed | Candidate | Parent | Result |
|---:|---|---:|---:|---|
| 1 | `9CB55A875F5B9` | 16 | 16 | tie |
| 2 | `CB396E925EDE2` | 33 | 33 | tie |
| 3 | `9619C48DC42EC` | 28 | 28 | tie |
| 4 | `6FE45EBC68949` | 16 | 16 | tie |
| 5 | `405B2ED9039E8` | 33 | 33 | tie |
| 6 | `BD3A3E021DE0F` | 16 | 25 | parent |
| 7 | `65E241B12F260` | 8 | 8 | tie |
| 8 | `9FD7F82A2AA86` | 20 | 21 | parent |
| 9 | `5AD8C55AF6422` | 33 | 33 | tie |
| 10 | `63FEF1BDDA8EB` | 16 | 16 | tie |

## Runtime integrity

- Candidate decisions: 799; eligible: 415; intervention intents: 106; safe takeovers: 73.
- CPU candidate latency: 5.72 ms p95, 65.51 ms maximum cold-start outlier; registered p95 ceiling: 20 ms.
- Runtime errors, illegal candidates, forbidden candidates, selected/final mismatches, and new CommunicationMod failures: 0.
- Both arms consumed all seeds in identical order; the parent arm had no candidate events and did not modify the candidate trace.
- The exact production CommunicationMod configuration was restored after each arm.

## Outcome

The candidate fails the preregistered paired-win, total-floor, and Act-2-entry conditions. Production r16 remains authoritative. This candidate cohort is closed without retry, threshold changes, or same-cohort tuning.
