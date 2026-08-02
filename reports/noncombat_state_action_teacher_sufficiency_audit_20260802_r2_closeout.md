# Non-Combat Teacher Sufficiency Audit R2 Closeout

## Result

The fresh v2 recovery registration published one canonical result and strict
recomputation matched every canonical byte. The terminal verdict is
`simpleagent_unsuitable_as_policy_quality_gate`; the registered next proposal
class is `outcome-backed-noncombat-rl-readiness`.

This closes the original teacher-sufficiency audit and its separate runtime
recovery. It does not authorize model fitting, simulator execution, gameplay,
formal RL, qualification, OPE reinterpretation, or policy promotion.

## Identity And Runtime

- implementation commit: `d86d73f84f07b2106e961ca29346941d7158fb93`
- registration commit: `fb9d5dc91efcb192436eb5157f378c75966c91de`
- registration SHA-256:
  `a0f5421169c8a28533167681c00589d9f927ba62dc6507523796d40d874689ff`
- train dataset SHA-256:
  `86cf82f7833ca6b7d3f4e58967f5768ef7292a2297d06af01819b783526227d0`
- external simulator commit:
  `7476a81954020087da31d41d16fddf475746ec2d`
- synthetic representation gate: 602 rows in 23.375 seconds, against a
  fixed 90-second limit
- canonical audit body: 34.938 seconds, against the unchanged 120-second
  limit

The consumed v1 registration and timeout failure remain immutable. R2 used one
fresh registration and one canonical execution; neither registration may be
retried.

## Canonical Findings

- 993/993 route and card-reward teacher actions reconstructed exactly from the
  bound SimpleAgent source.
- 602 rows had multiple candidates: 300 route and 302 card reward.
- Raw adapter dependency coverage had zero missing exact dependencies.
- Teacher-source, adapter-observable, legacy-hash-1024, and
  structured-hash-2048 each had zero conflicting semantic target groups, zero
  non-equivalent candidate aliases, and zero pairwise contradictions on this
  corpus.
- The structured projection still omits exact map topology/rooms, cached map
  path, and card offer order, but those omissions produced no observed alias or
  contradiction in the registered rows.
- All six fixed teacher-suitability checks failed: SimpleAgent plans a route
  only at map entry, reads neither current HP nor gold for route selection,
  applies card copy limits to the offer rather than the actual deck, reads no
  deck/run context for card reward, and does not value skip versus Singing
  Bowl.

The absence of representation conflicts establishes source closure for this
preserved train corpus. It does not convert SimpleAgent imitation into a policy
quality objective.

## Manual Closeout Audit

The post-recomputation read-only review confirmed:

- exact managed inventory: nine canonical artifacts plus one noncanonical
  execution journal;
- exact manifest hash closure for every canonical payload;
- `configuration.json` is byte-identical to the committed v2 registration;
- strict recomputation returned the same manifest and artifact hashes;
- source closure has zero reconstruction mismatches and zero blockers;
- the audit body stayed below the registered wall-time bound;
- all downstream authority fields remain false;
- the five relevant external source files remained clean and physically bound.

## Direction

SimpleAgent remains useful as an auxiliary regression oracle and deterministic
source reference. It must not be used as reward, ground truth, a promotion
gate, or a mandatory learned-policy target.

The next allowed capability is a separate read-only outcome-backed non-combat
RL readiness audit. It should inventory whether existing state/action records,
known-propensity support, terminal outcomes, reward attribution, and untouched
offline evaluation contracts are sufficient to preregister a bounded training
study. Until that audit has a positive, reproducible go verdict and a separate
training OpenSpec is approved, formal non-combat RL remains unauthorized.
