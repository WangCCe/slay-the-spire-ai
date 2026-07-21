# Adaptive Route Opportunity Audit: Frozen 2026-07-21 Cohort

## Result

The one resumed POC invocation completed with exit code `0`. The generated
`adaptive-route-opportunity-audit-v1` artifact has `integrity.status=valid` and
no diagnostics. Its SHA-256 is
`05e38f1169235a97811cf870e1ba24aba881610a61929fc086ad2edab6da2f2f`
over `224,605` bytes.

All 13 source identities matched the registered pre-run values before and after
the invocation. No source bytes changed, and the Slay the Spire process count
was zero both before and after the command.

## Exact Command

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\adaptive_route_opportunity_audit.py --ai-log D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log.1 --ai-log D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug_adaptive_20260721.log --decision-trace D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_decision_trace_adaptive_20260721.jsonl --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650652.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650754.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650802.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650867.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784650965.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651020.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651097.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651170.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651250.run --run D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1784651443.run --log-utc-offset-hours 8 --max-join-seconds 0.01 --output reports\adaptive_route_opportunity_audit_20260722.json
```

Parameters preserved in the JSON are `log_utc_offset_hours=8.0` and
`max_join_seconds=0.01`.

## Source Identities

| Kind | Ordered source path | Bytes | Lines | Parsed records | SHA-256 |
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

The decision trace contains 364 map records, 346 node-action records, and 18
boss-action records. The ten run sources are preserved in registered game order.

## Integrity

- Status: `valid`
- Diagnostics: none
- Registered source identity mismatches before or after execution: `0`
- Preserved canonical transition slots: game 1, game 5, and game 10 each have
  `null` at zero-based `path_per_floor[16]`, immediately after `B`.
- The canonical nulls are structural inter-act slots. They are not rooms,
  event resolutions, route divergences, or optional elites.
- Ten run records were accepted; all ten record `victory=false`.

## Deduplication

| Measure | Count |
| --- | ---: |
| Raw adaptive occurrences | 346 |
| Callback-independent records | 173 |
| Multiplicity 2 records | 173 |
| Other multiplicities | 0 |

The registered callback collapse is therefore exactly `346 -> 173`, with
multiplicity distribution `{2: 173}`.

## Opportunity Funnel

| Funnel stage | Count |
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

## Candidate-Generation Fallbacks

The JSON reports exactly four callback-independent
`candidate_generation_failed` fallbacks. They account for all four records that
are not complete candidate pairs (`173 - 169 = 4`). Because every
callback-independent record has multiplicity two, the four fallbacks correspond
to eight raw callback occurrences. They are not zero-versus-one opportunities
and contribute no aggressive selection or realized treatment.

The v1 JSON preserves the fallback aggregate but does not serialize four
separate fallback provenance objects. This report therefore retains the exact
machine-readable count without inventing per-fallback details.

## Sole Aggressive Case

- Identity: game 1, opportunity 8, Act 1 floor 7.
- Joined action: coordinate `[2, 7]`, trace symbol `M`, run symbol `M`, exact
  run compatibility.
- Selection: `aggressive`.
- Immediate coordinates: conservative `[2, 7]`, aggressive `[2, 7]`; classified
  `same`.
- Aggressive route matches: one,
  `[[2,7],[1,8],[1,9],[1,10],[1,11],[0,12],[0,13],[1,14]]`.
- Conservative route matches: two,
  `[[2,7],[1,8],[1,9],[1,10],[1,11],[1,12],[2,13],[2,14]]` and
  `[[2,7],[1,8],[1,9],[1,10],[1,11],[1,12],[2,13],[3,14]]`.
- Provable first divergence: candidate index 5 at map `y=12`, entering floor
  13; aggressive coordinate `[0, 12]`, conservative coordinate `[1, 12]`.
- Revocation: the next recorded map decision, Act 1 floor 8, selected
  `conservative` before the divergence.
- Treatment status: `revoked_before_divergence`; divergences taken `0` and
  realized optional elites `0`.

The sole aggressive policy selection therefore did not create an immediate
coordinate difference and did not survive long enough to realize route
treatment.

## Limitations

- This is a frozen observational audit of ten runs, not a counterfactual or
  causal value estimate.
- One aggressive selection and zero realized optional elites provide no basis
  for estimating the value of denied opportunities.
- Candidate symbol routes can remain coordinate-ambiguous. The audit counts
  treatment only where immediate coordinates or first divergence are provable.
- Run records do not contain map coordinates. Event `?` nodes may resolve to
  non-boss room symbols, and canonical post-boss nulls are transition slots.
- The v1 artifact aggregates candidate-generation fallbacks rather than
  preserving four per-fallback report objects.
- All ten runs ended without victory, so this cohort cannot establish a
  route-policy improvement.

## Stop Decision

Keep the conservative policy. Do not tune thresholds or defaults, rerun this
cohort, train from it, or promote a policy change. Any oracle or value study is
a separate capability and requires a separately approved OpenSpec change.
