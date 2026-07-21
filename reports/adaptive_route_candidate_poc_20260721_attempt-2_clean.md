# Adaptive Route Candidate POC: Attempt 2 Clean-Source PASS

## Decision

**PASS.** The sole formal clean-source requalification completed once with all
seven cases and 700 measured pairs. The aggregate median was `15.91075 ms`
and the maximum was `61.6691 ms`, within the unchanged limits of aggregate
median `<= 25.0 ms` and every measured pair `<= 100.0 ms`.

This Markdown report is derived from
`reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json` exactly
as recorded. JSON SHA-256:
`fcee81f1b112e4780175e925cdcb9df3596bd4c792b1552ac79aa9e21d92b85e`.

## Execution

Interpreter: `D:\anaconda\envs\stsai\python.exe`

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\benchmark_adaptive_route_candidates.py --fixture-root tests\fixtures\adaptive_route_maps --warmups 10 --samples 100 --output reports\adaptive_route_candidate_poc_20260721_attempt-2_clean.json --log .adaptive_route_poc\route.log
```

Provenance recorded in the JSON:

- Tested commit: `0ddaf5520b25e722036ce5beab5c24ec068814a8`
- Task 1 worktree: `clean`
- Evidence schema: `adaptive-route-candidate-poc-v1`
- Warm-ups: `10` excluded paired samples per case
- Measured samples: `100` paired samples per case, `700` total

## Fixture Contract

The four `legacy_characterization` cases use the shared legacy source
contract and each produced verified legal 15-node conservative and aggressive
routes. The three `full_height_json` cases satisfy the approved full-height
contract: fixture schema `adaptive-route-map-fixture-v1`, Act 1, exactly 15
layers (`y=0..14`), columns `x=0..6`, valid forward child edges, valid starts,
and at least 35 reachable nodes.

| Fixture | SHA-256 | Source | Warm-ups / measured | Median ms | P95 ms | Max ms |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `legacy-optional-elite-v1` | `098e2ae6b20fb4a698d86452c2fcb1c9821aef47a3acee70f7dfad435a12ca18` | `legacy_characterization` | 10 / 100 | 14.7525 | 27.9056 | 43.9234 |
| `legacy-forced-one-elite-v1` | `a189974bb274acf9105bdcd2c941bfa6a9a5f5ec92bc020391b7bc4db2cbfd01` | `legacy_characterization` | 10 / 100 | 11.97345 | 16.7306 | 21.3201 |
| `legacy-forced-two-elite-v1` | `78b607a3c94457cdd417515065198848fe896a734584c3cc775cd4036f47cf0c` | `legacy_characterization` | 10 / 100 | 15.41945 | 26.2845 | 33.5257 |
| `legacy-hp-drop-replan-v1` | `db26fc49fe1d1dce479c15d170ac40575a35b59e425a163c51fd494ada46e2b7` | `legacy_characterization` | 10 / 100 | 12.08615 | 21.0566 | 36.4968 |
| `full-height-sparse-v1` | `7eae28f6abe1d688d344da55ce112d1382480595db45e8bc3e15ae0bf5396339` | `full_height_json` | 10 / 100 | 18.88075 | 32.3367 | 61.6691 |
| `full-height-typical-v1` | `6ec1b6c163edaccef62ea9a341286d49562ac369fbc34bd036da0229e0ff78f5` | `full_height_json` | 10 / 100 | 18.7533 | 28.4233 | 40.0282 |
| `full-height-dense-v1` | `de5ca9ba2066d4ea2175fae1cf62d3d7421873ca8a46cb0d58cd37b97379eb1f` | `full_height_json` | 10 / 100 | 17.955 | 28.3904 | 59.8183 |

## Selected Routes

All paths below are the selected node IDs from the exact JSON evidence.

- `legacy-optional-elite-v1`: conservative `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`; aggressive `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`.
- `legacy-forced-one-elite-v1`: conservative `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`; aggressive `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.
- `legacy-forced-two-elite-v1`: conservative `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`; aggressive `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.
- `legacy-hp-drop-replan-v1`: conservative `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`; aggressive `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`.
- `full-height-sparse-v1`: conservative `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`; aggressive `[2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`.
- `full-height-typical-v1`: conservative `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`; aggressive `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`.
- `full-height-dense-v1`: conservative `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`; aggressive `[2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`.

## Aggregate And Auditability

| Fixtures | Measured pairs | Median ms | P95 ms | Max ms |
| ---: | ---: | ---: | ---: | ---: |
| 7 | 700 | 15.91075 | 26.9415 | 61.6691 |

The JSON retains `durations_ns` for every fixture (100 values each) and the
aggregate (700 values), allowing every percentile and maximum above to be
audited without rerunning the benchmark. Each recorded route has 15 nodes.

The canonical first FAIL evidence and immutable `attempt-1-fail` artifacts
remain preserved. This PASS consumed the sole formal clean-source
requalification; no retry remains under this change.
