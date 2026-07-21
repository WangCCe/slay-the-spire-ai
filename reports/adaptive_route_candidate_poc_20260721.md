# Adaptive Route Candidate POC - 2026-07-21

## Decision

PASS. All 300 measured paired route-generation samples completed. Aggregate
median paired latency was 18.36535 ms (limit: 25.0 ms) and the maximum was
96.6285 ms (limit: 100.0 ms).

## Environment And Command

- Interpreter: `D:\anaconda\envs\stsai\python.exe`
- Git commit at POC start: `727177bc4ce600b9499fd24bbd7f9b08b8bd1eb0`
- Route log: `.adaptive_route_poc\route.log`

```powershell
D:\anaconda\envs\stsai\python.exe analysis_scripts\benchmark_adaptive_route_candidates.py --fixture-root tests\fixtures\adaptive_route_maps --warmups 10 --samples 100 --output reports\adaptive_route_candidate_poc_20260721.json --log .adaptive_route_poc\route.log
```

The command exited `0`. Each fixture used ten excluded warm-up pairs followed
by 100 measured pairs. A pair constructed separate conservative and aggressive
agents from identical fixture state, started `perf_counter_ns` immediately
before conservative `generate_map_route()`, and stopped it immediately after
aggressive generation returned. Normal route logging was written through the
DEBUG file handler before timing began.

## Fixtures

Every fixture uses schema `adaptive-route-map-fixture-v1`, 15 layers
(`y=0..14`), columns within `0..6` (actual columns `0..2`), 35 reachable nodes,
and one child per reachable nonterminal node. The short third branch merges
into the second branch at `(1, 5)`. Elite/rest placement varies by fixture.

| Fixture | SHA-256 | Median ms | P95 ms | Max ms | Conservative path | Aggressive path |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `full-height-sparse-v1` | `7eae28f6abe1d688d344da55ce112d1382480595db45e8bc3e15ae0bf5396339` | 19.15595 | 31.5354 | 45.1181 | `0,0,0,0,0,0,0,0,0,0,0,0,0,0,0` | `2,2,2,2,2,1,1,1,1,1,1,1,1,1,1` |
| `full-height-typical-v1` | `6ec1b6c163edaccef62ea9a341286d49562ac369fbc34bd036da0229e0ff78f5` | 17.5075 | 29.3177 | 46.7085 | `0,0,0,0,0,0,0,0,0,0,0,0,0,0,0` | `1,1,1,1,1,1,1,1,1,1,1,1,1,1,1` |
| `full-height-dense-v1` | `de5ca9ba2066d4ea2175fae1cf62d3d7421873ca8a46cb0d58cd37b97379eb1f` | 18.2446 | 38.2089 | 96.6285 | `1,1,1,1,1,1,1,1,1,1,1,1,1,1,1` | `2,2,2,2,2,1,1,1,1,1,1,1,1,1,1` |

Aggregate: three fixtures, 300 measured pairs, median `18.36535 ms`, p95
`32.9989 ms`, maximum `96.6285 ms`.

The fixture identities, durations, paths, aggregate values, and PASS status are
preserved in `reports/adaptive_route_candidate_poc_20260721.json`.
