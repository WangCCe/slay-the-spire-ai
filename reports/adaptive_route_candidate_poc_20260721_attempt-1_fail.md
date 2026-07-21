# Adaptive Route Candidate POC - 2026-07-21

## Decision

FAIL / BLOCKED. The second required production qualification run measured one
paired sample at 105.1622 ms, above the 100.0 ms per-sample limit. The
aggregate median was 16.6877 ms, below the 25.0 ms limit, but both gates are
required. No retry, threshold change, fixture reduction, or logging reduction
was performed after this failure.

## Provenance And Command

- Interpreter: `D:\anaconda\envs\stsai\python.exe`
- Tested HEAD: `db0808123ff4d3a390c8626308912fe4eedf494c`
- Tested worktree: dirty, limited to the Task 1 review follow-up changes in
  `analysis_scripts/benchmark_adaptive_route_candidates.py`, both Task 1 test
  modules, this POC evidence, and the Task 1 OpenSpec status.
- Reproduce provenance before a follow-up revision with:

```powershell
git rev-parse HEAD
git diff -- analysis_scripts/benchmark_adaptive_route_candidates.py tests/test_adaptive_route_candidate_benchmark.py tests/test_map_routing_safety.py reports/adaptive_route_candidate_poc_20260721.json reports/adaptive_route_candidate_poc_20260721.md openspec/changes/add-adaptive-elite-routing-baseline/tasks.md
```

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\benchmark_adaptive_route_candidates.py --fixture-root tests\fixtures\adaptive_route_maps --warmups 10 --samples 100 --output reports\adaptive_route_candidate_poc_20260721.json --log .adaptive_route_poc\route.log
```

The command exited `1`. The executable guard requires
`D:\anaconda\envs\stsai\python.exe`; qualification rejects fewer than ten
warm-ups or fewer than 100 measured samples per case.

## Coverage

Qualification measured all four shared characterization maps used by
`tests/test_map_routing_safety.py` and the three versioned full-height JSON
fixtures. Each case received ten excluded warm-up pairs and 100 measured pairs.
Every candidate route was nonempty, exactly 15 nodes, present in its map, and
connected by legal child edges.

| Case | Source | SHA-256 | Median ms | P95 ms | Max ms |
| --- | --- | --- | ---: | ---: | ---: |
| `legacy-optional-elite-v1` | shared legacy characterization | `098e2ae6b20fb4a698d86452c2fcb1c9821aef47a3acee70f7dfad435a12ca18` | 16.2866 | 26.1687 | 38.2777 |
| `legacy-forced-one-elite-v1` | shared legacy characterization | `a189974bb274acf9105bdcd2c941bfa6a9a5f5ec92bc020391b7bc4db2cbfd01` | 16.32385 | 25.9926 | 105.1622 |
| `legacy-forced-two-elite-v1` | shared legacy characterization | `78b607a3c94457cdd417515065198848fe896a734584c3cc775cd4036f47cf0c` | 15.55855 | 22.9241 | 32.2079 |
| `legacy-hp-drop-replan-v1` | shared legacy characterization | `db26fc49fe1d1dce479c15d170ac40575a35b59e425a163c51fd494ada46e2b7` | 11.03895 | 18.0705 | 24.6097 |
| `full-height-sparse-v1` | JSON fixture | `7eae28f6abe1d688d344da55ce112d1382480595db45e8bc3e15ae0bf5396339` | 17.8138 | 31.3472 | 45.0511 |
| `full-height-typical-v1` | JSON fixture | `6ec1b6c163edaccef62ea9a341286d49562ac369fbc34bd036da0229e0ff78f5` | 18.2367 | 34.4585 | 48.7645 |
| `full-height-dense-v1` | JSON fixture | `de5ca9ba2066d4ea2175fae1cf62d3d7421873ca8a46cb0d58cd37b97379eb1f` | 19.17685 | 30.1952 | 42.6268 |

Aggregate: seven cases, 700 measured pairs, median `16.6877 ms`, p95
`27.424 ms`, maximum `105.1622 ms`. The full machine-readable evidence,
including `tested_head=db0808123ff4d3a390c8626308912fe4eedf494c` and
`task1_worktree=dirty`, is in `reports/adaptive_route_candidate_poc_20260721.json`.

## Next Step

OpenSpec task 1.4 remains unchecked and the adaptive gameplay implementation
must not proceed until the proposal is revised and requalified.
