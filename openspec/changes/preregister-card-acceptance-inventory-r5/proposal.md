## Why

R4 published a valid compact inventory but became terminal when an unregistered
review command crossed the verification boundary before distinct verification
authority existed. The production verifier now enforces separate canonical
authority, an immutable one-shot execution receipt, bounded flushed completion,
and legacy-command rejection, so parent task 6.2 can proceed only through a new
r5 identity.

## What Changes

- Bind r5 to pushed source commit `525c302df`, which contains the reviewed and
  archived verification hardening. Preserve r1-r4 as terminal predecessors and
  do not read, retry, repair, replace, or register their unverified inventory
  content.
- Publish one distinct compact-v4 r5 inventory request, delegated approval,
  authorization, fresh launch observation, output/attempt paths, and exact
  source/path preflight. Build may start at most once after a pushed clean
  pre-start gate.
- After successful build publication only, publish a separate canonical
  `inventory-verification` request, approval, authorization, and fresh launch.
  Invoke only the hardened six-file `verify-inventory` CLI, whose own immutable
  receipt must precede inventory and historical evidence access.
- Require exact agreement among build completion, compact inventory, build and
  verification receipts, source-only reconstruction, and the standalone
  verifier before publishing one canonical all-false `512/128/512`
  registration and completing parent task 6.2.
- Success is the independently verified bounded registration, not dispatch,
  request publication, build publication, or CLI completion alone. Parent task
  6.3 and every training, native/model/environment, evaluation, gameplay,
  CommunicationMod, OPE, qualification, promotion, and downstream authority
  remain false.
- Live evidence is the terminal r4 postmortem, hardening implementation and
  static review through `6e2937a00`, archived contract through `525c302df`,
  owning `265 passed`, and full gate `5803 passed, 18 skipped`.
- Before any build or verification process is created, rollback removes only
  additive uncommitted r5 artifacts. After process creation, invocation,
  failure, receipt, and output evidence remain preserved even if no receipt was
  written, and the identity is terminal on failure; rollback never retries,
  resumes, tunes, raises bounds, changes cohorts, or substitutes authority.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Add the distinct r5
  compact-inventory, hardened verification, standalone agreement, and all-false
  registration gate after terminal r4.
- `noncombat-card-acceptance-inventory-source-boundary`: Bind r5 source/path
  preflight to the pushed hardening source, every terminal predecessor, exact
  new write surfaces, and absence checks without predecessor inventory-content
  access.

## Impact

The change initially adds only repo-local OpenSpec and bounded control-plane
evidence. Later execution reuses the existing Windows production interpreter,
source-only inventory builder, hardened verifier, standing delegation, and
standalone verifier. It changes no gameplay policy, simulator, RL objective,
checkpoint, CommunicationMod configuration, dependency, or production import
path, and it does not authorize training.
