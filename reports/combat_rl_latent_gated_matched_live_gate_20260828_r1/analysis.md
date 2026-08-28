# Latent-Gated Matched Live Gate

## Decision

Retain production r16 and close this candidate cohort. The candidate runtime was
technically healthy, but it failed the preregistered live outcome gate.

## Matched Outcome

| Metric | Candidate | Parent r16 |
|---|---:|---:|
| Completed games | 10 | 10 |
| Paired floor wins | 0 | 2 |
| Floor ties | 8 | 8 |
| Total floors | 168 | 184 |
| Victories | 0 | 0 |
| Act 2 entries | 2 | 2 |
| Act 2 boss reaches | 1 | 2 |
| Act 3 entries | 0 | 0 |

The candidate lost seed pair 3 by 11 floors and seed pair 9 by 5 floors. It did
not win any pair. It therefore failed paired floor wins, total floors, and Act 2
boss reach non-regression.

## Runtime Evidence

Candidate mode recorded 1,108 decisions and six transient discards in one
contiguous session. It produced 601 actual takeovers with zero error events,
100% parent parity, 100% legal candidate actions, and 100% legal final actions.
Adapter p95 latency was 20.36 ms against the registered 100 ms ceiling.

Existing outer guards changed 138 selected proposals, so selected-to-final
agreement was 87.55%. This was expected and remained fully attributable in the
trace.

Both arms completed the registered seed order without policy/runtime errors.
CommunicationMod replaced only the first properties comment with a timestamp;
the launch commands remained semantically exact. The canonical production
configuration was restored between arms and after the gate with SHA-256
`0991895790bc73d3d21a05731bf402228cf0c510a4217aa841ced026016760e7`.

## Boundary

This result does not support promotion, threshold tuning, or another attempt on
the same cohort. A later candidate must come from materially new offline or
simulator evidence and use a separately preregistered fresh cohort.
