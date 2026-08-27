# Guard-aware bootstrap registration review

## Verdict

`ready_for_single_execution`

The registration isolates one behavior-bearing variable: raw frozen-parent
greedy bootstrap versus frozen-parent deployment-guard bootstrap. Collection,
parent initialization, replay targets, anchoring, optimizer budget, seeds, and
evaluation are otherwise fixed.

## Source binding

- The Windows Python native-load preflight succeeded without additional DLL
  directories.
- The immutable adapter module SHA-256 is
  `195678b7fc6bf69815f3d2971404afb8ce72fb666700edf4203383429caf1009`.
- The simulator remains at commit
  `7476a81954020087da31d41d16fddf475746ec2d` with the already-known dirty
  source identity
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`.
  The experiment binds that source hash and both submodule commits instead of
  relying on a clean-worktree claim.
- The runner, bridge, trainer, replay buffer, item export, and production-r16
  parent hashes match the registration.

## Cohort review

The training range `176000..177023` and evaluation range `178000..178255` are
internally disjoint. A structured scan of every tracked combat LightSTS
registration found no use of either range. The immediately preceding registered
ranges end at evaluation seed `174255`.

## Execution boundary

Run the raw-greedy control first and the deployment-guard candidate second. Each
arm has one attempt and a two-hour wall limit. Any arm failure closes the
experiment without retry, resume, seed replacement, or parameter change. A
successful candidate authorizes only a separately registered larger simulator
confirmation; it does not authorize gameplay, packaging, or promotion.
