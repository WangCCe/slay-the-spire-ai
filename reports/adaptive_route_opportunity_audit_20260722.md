# Adaptive Route Opportunity Audit: Final Frozen-Cohort Evidence

## Final Disposition

The final analysis invocation exited `0`. The current machine artifact uses
schema `adaptive-route-opportunity-audit-v1`, reports
`integrity.status=valid`, and has no diagnostics. It is `232,184` bytes with
SHA-256 `252e57b7830d7d10027ae223a023b6d30aea02470cdb89263d08511ff8f65955`.

The evidence supports an opportunity-and-uptake audit only. Keep the
conservative route policy. Do not tune thresholds or defaults, rerun this
cohort, train from it, or promote a policy change. Any oracle or value study
requires a separate approved OpenSpec change.

## Analysis Lineage

This path contains the final artifact, but Task 4 had three analysis
invocations. The two earlier artifacts were deliberately superseded. Their
bytes are no longer at the output path, so this report preserves their observed
identities and dispositions without implying that the current JSON contains
them.

1. **Initial fail-closed invocation.** The registered command exited `1` and
   wrote a `2,251` byte invalid artifact with SHA-256
   `b29a72f4aa1c8823b5ba9b09275f5fd0ab32ced9978ac05af2631d3d95c5d400`.
   Its diagnostic was
   `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650652.run:None: run path_per_floor must contain only valid room symbols`.
   Read-only inspection showed a canonical post-boss `null` transition slot at
   zero-based `path_per_floor[16]`. The failed artifact was preserved long
   enough to diagnose the analysis-format defect, then overwritten only after
   a reviewed fix was authorized.
2. **Reviewed transition-slot fix and superseding valid invocation.** Commit
   `56d9cefcd90f055ceb1d5c273fdd32cbdba7e980` (`fix: preserve canonical run
   transition slots`) preserved only `null` immediately after `B` and retained
   fail-closed behavior elsewhere. The next authorized invocation exited `0`
   and wrote a `224,605` byte valid artifact with SHA-256
   `05e38f1169235a97811cf870e1ba24aba881610a61929fc086ad2edab6da2f2f`,
   committed in `4469ebc4bf4472baaad087b77204df2ca3d94c92`.
3. **Fallback-provenance review.** Task 4 review found three Important evidence
   issues: missing durable failed/resumed lineage, operator controls stated as
   if they were JSON fields, and no per-fallback provenance. Fallback evidence
   was implemented in
   `db534c38d45ef0c0401f0448de6872cff1b4676b`, strengthened by review tests in
   `45d6f162adc2e3a31cb20eb08d151494771208d8`, and registered after independent
   approval at reviewed HEAD
   `9eb809f53edc062f32d0524cf50efd34b76de98f`.
4. **Final invocation.** One final authorized analysis invocation ran at that
   reviewed HEAD against the same 13 frozen source identities. It exited `0`
   and overwrote only the prior valid JSON with the current `232,184` byte
   artifact identified above. This final artifact adds four separately
   auditable fallback objects while retaining every previously registered
   count and treatment result.

## Exact Final Command

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\adaptive_route_opportunity_audit.py --ai-log D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log.1 --ai-log D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log --decision-trace D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace_adaptive_20260721.jsonl --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650652.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650754.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650802.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650867.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650965.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651020.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651097.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651170.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651250.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651443.run --log-utc-offset-hours 8 --max-join-seconds 0.01 --output reports\adaptive_route_opportunity_audit_20260722.json
```

The final JSON records `log_utc_offset_hours=8.0` and
`max_join_seconds=0.01`.

## Operator-Observed Controls

The following are operator-observed boundary controls copied into this durable
report. They are **not fields in the final JSON**. The final JSON contains one
source-identity snapshot for the final analysis and contains no process
observations, no pre/post manifests, and no continuous process monitoring.

| Boundary observation | Observed UTC | Registered source hashes | Observed `SlayTheSpire` process count |
| --- | --- | --- | ---: |
| Before final command | `2026-07-21T22:30:51.1720734Z` | 13/13 matched | 0 |
| After final command | `2026-07-21T22:31:41.3503961Z` | 13/13 matched | 0 |

At both observed boundaries, SHA-256 and byte count for all 13 source paths
matched the registration below. This establishes equality at those boundaries;
it is not a JSON-backed second snapshot and does not prove the absence of an
unobserved transient process between observations. The operator did not launch
or rerun the game.

## Final JSON Source Snapshot

These identities are fields in the final JSON and appear in registered command
order.

| Kind | Source path | Bytes | Lines | Parsed records | SHA-256 |
| --- | --- | ---: | ---: | ---: | --- |
| AI log 1 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log.1` | 10,485,706 | 111,379 | 308 | `72f73e094c33883ae53f724c8fd48ea94482503fcce503ebb4981210c9c6268a` |
| AI log 2 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log` | 2,751,552 | 29,171 | 38 | `e0388bcfb9d8992ec325e14f99076d5b7f5cfbda7eaab1b45aae60da7dd2a2fc` |
| Decision trace | `D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace_adaptive_20260721.jsonl` | 9,739,213 | 2,768 | 2,768 | `259a9c07f803c32d70caf41eb062e4c354b09d5223d18cc462f71d260d9f899f` |
| Run 1 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650652.run` | 5,610 | 1 | 1 | `ca10fa2f5cda7fab3b7d27cf5111ccd0c78bbdaf377bc4257546ecf118f38b4c` |
| Run 2 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650754.run` | 3,529 | 1 | 1 | `5e3867045bfc93d57cf5c1756609bb56fa1e3f0bb4ca920171966b36746fad52` |
| Run 3 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650802.run` | 2,289 | 1 | 1 | `ffaff203a15b007e0c97953b57fb56f5e506147db358f1801db1f9bf6b288d88` |
| Run 4 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650867.run` | 3,482 | 1 | 1 | `b88b9aadd596977c9e112ca7ef2eb71da820550621279cde8f7660e229f08b97` |
| Run 5 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650965.run` | 5,174 | 1 | 1 | `86656c3eefdef15d5e6e8bbd39eed4f931539696b3958fa8bc5d35e899338b05` |
| Run 6 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651020.run` | 2,738 | 1 | 1 | `ce0428e6105ad5ddcee62e28f181f6c157fe0453f17d811b5eb7480b30553b43` |
| Run 7 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651097.run` | 3,357 | 1 | 1 | `a45f57d1691ae833138c2f24337a703d12b5a9f7becfd21316af9d3da7b8cf64` |
| Run 8 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651170.run` | 3,240 | 1 | 1 | `3dddfd0da4b7c0a347fdc1497881a72a665df6e70967d283ecb01088ff3b3f91` |
| Run 9 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651250.run` | 3,338 | 1 | 1 | `c5f2f3df0ebb9191cdb2765f3bc63335d1748680f28215c5e583ba486153ef01` |
| Run 10 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651443.run` | 5,652 | 1 | 1 | `8873a26cca8ff21cb01263937b670761e0007f8f3bef92cb459146a24e135678` |

The decision-trace snapshot additionally reports 364 map records, 346
node-action records, and 18 boss-action records. The JSON accepted all ten run
records in registered order. All ten have `victory=false`. It preserves
canonical post-boss `null` slots only for games 1, 5, and 10 at zero-based
`path_per_floor[16]`, immediately after `B`.

## Integrity And Deduplication

| JSON-backed measure | Value |
| --- | ---: |
| Integrity status | `valid` |
| Integrity diagnostics | 0 |
| Raw adaptive occurrences | 346 |
| Callback-independent records | 173 |
| Records with multiplicity 2 | 173 |
| Other multiplicities | 0 |

The callback collapse is exactly `346 -> 173`; the multiplicity distribution
is `{2: 173}` and sums back to 346 raw occurrences.

## Opportunity Funnel

| JSON-backed funnel stage | Count |
| --- | ---: |
| Adaptive occurrences | 346 |
| Callback-independent records | 173 |
| Candidate-generation fallbacks | 4 |
| Complete candidate pairs | 169 |
| Zero-versus-one opportunities | 58 |
| Act 1 zero-versus-one opportunities | 54 |
| Aggressive selections | 1 |
| Same immediate coordinate | 1 |
| Different immediate coordinate | 0 |
| Ambiguous immediate coordinate | 0 |
| Provable first divergences | 1 |
| Selections revoked before divergence | 1 |
| Routes left before divergence | 0 |
| Divergences taken | 0 |
| Realized optional elites | 0 |

## Four Auditable Fallbacks

The final JSON contains exactly four fallback objects. Their stable ordinals are
`1,2,3,4`; their list length equals
`funnel.candidate_generation_fallbacks=4`; each has multiplicity two; total
multiplicity is eight; all four complete payload identities are unique; and all
eight occurrence line identities are unique. Each occurrence was reconciled to
the exact frozen log line named below.

All eight occurrences use source
`D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log.1`.
All four run corroborations use
`D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650965.run`.

| Ordinal | Game | Act/floor | Multiplicity | Current -> action | Next coordinates | Run corroboration |
| ---: | ---: | --- | ---: | --- | --- | --- |
| 1 | 5 | 2/18 | 2 | `[1,0] -> [1,1]` | `[[1,1],[2,1],[3,1],[4,1]]` | exact `?` / `?` |
| 2 | 5 | 2/19 | 2 | `[1,1] -> [0,2]` | `[[0,2],[1,2],[2,2],[5,2]]` | exact `?` / `?` |
| 3 | 5 | 2/20 | 2 | `[0,2] -> [0,3]` | `[[0,3],[1,3],[2,3],[4,3]]` | exact `?` / `?` |
| 4 | 5 | 2/21 | 2 | `[0,3] -> [1,4]` | `[[1,4],[3,4],[4,4]]` | exact `M` / `M` |

### Fallback 1

Complete payload identity:

```text
outcome=candidate_generation_failed character=IRONCLAD act=2 floor=18 state_valid=true hp=54/80 hp_pct=0.675000 deck=6 potion=0 relic=2 elite_seen=false last_rest_floor=none candidate_pair=generation_failed conservative_candidate=unavailable aggressive_candidate=unavailable minimum_elites=unavailable added_elites=unavailable fallback_candidate=mode:conservative,start_y:1,symbols:?/?/?/M/R/M/?/T/M/?/M/R/M/R,elite_count:0,elite_floors:none,recovery_before:none,recovery_after:none budget=0 selected=conservative reasons=candidate_generation_failed
```

| Occurrence | Line | Timestamp | Join delta seconds |
| ---: | ---: | --- | ---: |
| 1 | 65,124 | `2026-07-22T00:22:25.337000` | `0.001` |
| 2 | 65,169 | `2026-07-22T00:22:25.410000` | `0.002` |

### Fallback 2

Complete payload identity:

```text
outcome=candidate_generation_failed character=IRONCLAD act=2 floor=19 state_valid=true hp=54/80 hp_pct=0.675000 deck=6 potion=0 relic=2 elite_seen=false last_rest_floor=none candidate_pair=generation_failed conservative_candidate=unavailable aggressive_candidate=unavailable minimum_elites=unavailable added_elites=unavailable fallback_candidate=mode:conservative,start_y:2,symbols:?/?/M/R/M/?/T/M/?/M/R/M/R,elite_count:0,elite_floors:none,recovery_before:none,recovery_after:none budget=0 selected=conservative reasons=candidate_generation_failed
```

| Occurrence | Line | Timestamp | Join delta seconds |
| ---: | ---: | --- | ---: |
| 1 | 65,230 | `2026-07-22T00:22:25.816000` | `0.002` |
| 2 | 65,273 | `2026-07-22T00:22:25.893000` | `0.001` |

### Fallback 3

Complete payload identity:

```text
outcome=candidate_generation_failed character=IRONCLAD act=2 floor=20 state_valid=true hp=20/80 hp_pct=0.250000 deck=7 potion=0 relic=2 elite_seen=false last_rest_floor=none candidate_pair=generation_failed conservative_candidate=unavailable aggressive_candidate=unavailable minimum_elites=unavailable added_elites=unavailable fallback_candidate=mode:conservative,start_y:3,symbols:?/M/R/M/?/T/M/?/M/R/M/R,elite_count:0,elite_floors:none,recovery_before:none,recovery_after:none budget=0 selected=conservative reasons=candidate_generation_failed
```

| Occurrence | Line | Timestamp | Join delta seconds |
| ---: | ---: | --- | ---: |
| 1 | 65,966 | `2026-07-22T00:22:35.834000` | `0.001` |
| 2 | 65,989 | `2026-07-22T00:22:35.893000` | `0.002` |

### Fallback 4

Complete payload identity:

```text
outcome=candidate_generation_failed character=IRONCLAD act=2 floor=21 state_valid=true hp=20/80 hp_pct=0.250000 deck=7 potion=0 relic=2 elite_seen=false last_rest_floor=none candidate_pair=generation_failed conservative_candidate=unavailable aggressive_candidate=unavailable minimum_elites=unavailable added_elites=unavailable fallback_candidate=mode:conservative,start_y:4,symbols:M/R/M/?/T/M/?/M/R/M/R,elite_count:0,elite_floors:none,recovery_before:none,recovery_after:none budget=0 selected=conservative reasons=candidate_generation_failed
```

| Occurrence | Line | Timestamp | Join delta seconds |
| ---: | ---: | --- | ---: |
| 1 | 66,028 | `2026-07-22T00:22:36.243000` | `0` |
| 2 | 66,049 | `2026-07-22T00:22:36.309000` | `0.001` |

## Sole Aggressive Case

- Identity: game 1, opportunity 8, Act 1 floor 7.
- Joined action: coordinate `[2,7]`, trace symbol `M`, run symbol `M`, exact
  run compatibility.
- Selection: `aggressive`.
- Conservative and aggressive immediate coordinates: `[2,7]`; classification
  `same`.
- Aggressive route match:
  `[[2,7],[1,8],[1,9],[1,10],[1,11],[0,12],[0,13],[1,14]]`.
- Conservative route matches:
  `[[2,7],[1,8],[1,9],[1,10],[1,11],[1,12],[2,13],[2,14]]` and
  `[[2,7],[1,8],[1,9],[1,10],[1,11],[1,12],[2,13],[3,14]]`.
- Provable first divergence: candidate index 5 at map `y=12`, entering floor
  13; aggressive `[0,12]`, conservative `[1,12]`.
- Revocation: Act 1 floor 8 selected `conservative` before divergence.
- Treatment status: `revoked_before_divergence`; divergences taken `0`;
  realized optional elites `0`.

The one aggressive policy selection produced neither an immediate coordinate
difference nor realized route treatment.

## Limitations

- This is a frozen observational audit of ten runs, not a counterfactual or
  causal value estimate.
- One aggressive selection and zero realized optional elites do not estimate
  the value of denied opportunities.
- Candidate symbol routes can remain coordinate-ambiguous; treatment is counted
  only where immediate coordinates or first divergence are provable.
- Run records lack map coordinates. Event `?` nodes can resolve to non-boss
  room symbols, and canonical post-boss nulls are structural transition slots.
- All ten runs ended without victory, so this cohort cannot establish a route
  policy improvement.
- The operator-observed boundary controls are durably labeled here but are not
  part of the machine artifact and are not continuous monitoring evidence.

## Stop Decision

The final artifact makes the four fallback records auditable but does not alter
the treatment conclusion. Keep conservative. No tuning, cohort rerun, training,
or policy promotion is authorized. Any oracle or value study is a separate
change.
