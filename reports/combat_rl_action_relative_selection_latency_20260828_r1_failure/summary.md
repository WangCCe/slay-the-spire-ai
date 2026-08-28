# Action-Relative Selection Latency Failure

- Decision: `offline_latency_preflight_failed`
- Failure: prediction parity failed during the first warmup comparison
- Official invocations: 1
- Registered output or staging created: no
- Live r2, gameplay, and training started: no
- Threshold, artifact, checkpoint, and corpus changed: no
- Closure: roll back the runtime optimization and do not sync the failed requirement
