# Route/Card Residual-Ranker POC Preflight

## Conclusion

The terminal train-only residual POC is ready for exactly one registered
execution, which internally performs one primary comparison and one identical
replay. No real-corpus model fit has occurred, and the canonical output
directory did not exist at preflight close.

## Frozen Identity

- Registration SHA-256:
  `eaf3e5f493d1686ca2cbff87571eee5ed1fa375c5e364a7d7d9cf7c568677676`
- Implementation commit:
  `737d5841939adcd372b04f3351c16d482c782e53`
- Implementation source SHA-256:
  `4d4eaef37715affa429d7ed1fe1d2b4e59d6a3f12a12cd05cc9b4d92d7a1551c`
- Train dataset SHA-256:
  `86cf82f7833ca6b7d3f4e58967f5768ef7292a2297d06af01819b783526227d0`
- Structured POC lineage verdict:
  `poc_valid_without_structured_candidate`
- Runtime: Windows Python `3.10.18`, PyTorch `2.5.1`.

The independent identity recheck reproduced the implementation source hash,
runtime, train dataset identity, and structured lineage verdict.

## Verification

- Focused residual POC regressions: `6 passed in 36.37s`.
- Python compilation: passed.
- Strict change validation: passed.
- Registered commit gate on the Windows host: `3257 passed, 11 skipped in
  242.88s`; gate total `246.04s`, exit code `0`.

An earlier sandboxed invocation is invalid infrastructure evidence, not a test
failure. It reached the suite but produced `WinError 5` across temporary-path
tests because its generated basetemp ACL allowed only `OWNER RIGHTS`, `SYSTEM`,
and `Administrators`, excluding `CodexSandboxUsers`. The same registered gate
passed under the owning Windows user without changing tests, manifest, source,
or registration. Do not count or rerun the sandbox attempt as a model trial.

## Sole Execution

Run only this checked-in command after its registration commit is pushed:

```powershell
D:\anaconda\envs\stsai\python.exe -m analysis_scripts.noncombat_route_card_residual_ranker_poc run --input reports\noncombat_route_card_residual_ranker_poc_20260802_input.json --output-dir reports\noncombat_route_card_residual_ranker_poc_20260802
```

The command may execute once. It performs the registered primary and replay;
there is no second command, alternate schedule, threshold change, model retry,
or reuse of this corpus after observing the verdict.

## Boundaries

- No native simulator, validation/final cohort, new seed, gameplay, outcome,
  reward, checkpoint, DAgger, formal RL, qualification, or promotion is
  authorized.
- Event/shop must delegate exactly to the shared legacy base. Route/card are
  the only learned residual categories.
- A pass authorizes only a separate fresh-study proposal. A valid negative ends
  baseline-imitation model trials on this corpus.
