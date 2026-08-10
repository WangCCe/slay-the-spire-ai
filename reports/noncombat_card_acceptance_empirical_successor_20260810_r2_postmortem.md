# Card-Acceptance Inventory r2 Terminal Postmortem

## Decision

The sole authorized r2 `build-inventory` invocation is terminal. It failed
during pre-start control-module import with
`ModuleNotFoundError: No module named 'analysis_scripts'`. The invocation
budget is consumed even though the request-bound started receipt was not
created. r2 SHALL NOT be retried, resumed, repaired in place, or used to create
an inventory registration.

During the failed build invocation, no seed, candidate blob, Git source or
repository evidence, native module, model, environment, game, or
CommunicationMod state was accessed. No cohort was materialized and no
training, evaluation, qualification, promotion, or gameplay operation
occurred. The separate pre-start gate had already performed its registered
source-only repository checks.

## Verified Boundary

The invocation used execution boundary commit
`1f00a559f0431d0764130a4e709e8a4a17844e12` and request source commit
`8e2a6f382c9c271c0b00cfdd3e76eddcb01bc8eb`. Focused receipt/source tests
passed 13 tests, the complete seed-inventory file passed 23 tests, and global
strict OpenSpec validation passed 83 items before the invocation.

The canonical failure is
`d44f6d900c902d94af20fba365725e9cc46c423a3ab10cbcedf16747e80ec3fb`.
Independent review `9c917fb424e5b082680ba1b875d0557a5a84cb332e64478e5963d9dc7cd04104`
found no actionable issue and verified that output, staging, attempts, and
started-receipt paths remained absent. The terminal evidence was committed and
pushed at `ed65be20e0b280bf23aa435c5a6775607348ac53`.

## What Worked

- The r1 generated-root defect was repaired and the source-only path preflight
  classified the consumed readiness staging root before blob access.
- Request-bound durable receipt enforcement and its partial-receipt regressions
  were implemented, reviewed, and pushed before r2 authority publication.
- The r2 request, approval, authorization, and launch observation were distinct,
  digest-bound, corrected against the actual human message, and independently
  reviewed before invocation.
- The failure remained before Git source discovery and all empirical operations,
  so the fail-closed authority boundary held.

## Failure Analysis

The pre-start checks did not reproduce the registered process entrypoint. The
manual import probe inserted the repository root into `sys.path`, while the
authorized command used `python -I <script-path>`. In isolated script mode the
repository root is absent from `sys.path`; the control-plane validator then
failed while importing the configured control module
`analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment`.

The durable receipt correctly represents a started build after authority and
source validation, but it is not the only one-shot boundary. The r2 proposal,
spec, design, and task contract separately allowed at most one process
invocation. An early import failure therefore leaves the receipt layer
unconsumed without restoring the r2 invocation budget.

## Next Gate

Any successor must use a new r3 request id, output root, source commit, request,
approval, authorization, and launch observation. Before publishing that
authority chain, it must:

1. Provide a supported isolated entrypoint that can import its control-plane
   module under the exact registered interpreter, working directory, and `-I`
   mode.
2. Add a regression or source-only subprocess smoke that exercises that exact
   dispatch and exits before receipt creation, source discovery, blob reads, or
   seed access.
3. Bind the tested command and entrypoint identity into the r3 pre-start gate.
4. Preserve r1 and r2 as terminal and grant no native, model, environment,
   training, evaluation, gameplay, qualification, or promotion authority.

This postmortem authorizes no r3 invocation or downstream RL operation.
