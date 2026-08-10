# Card-Acceptance Inventory r3 Terminal Postmortem

## Decision

The sole authorized r3 `build-inventory` invocation is terminal. It created and
fsynced the immutable request-bound receipt, discovered repository seed
evidence, materialized the requested cohorts, validated the in-memory artifact,
and atomically published `seed_inventory.json`. The CLI then attempted to write
the complete 2,675,460,894-byte artifact to stdout in one operation and failed
with `OSError: [Errno 22] Invalid argument`.

Because this was a post-receipt CLI failure, r3 SHALL NOT be retried, resumed,
verified, repaired in place, or used to create an inventory registration. The
published artifact remains `published_unverified`; its content, source rows,
exclusions, cohorts, role digests, and inventory self-digest were not accepted
by the distinct verifier. Parent tasks 6.2 and 6.3 remain incomplete.

## Verified Boundary

The invocation started from pushed execution boundary commit
`dcec99dce9e76f707d40b0c4fbf65c239c97b586`. The receipt file digest is
`9d4be5cbdac1af1432306ca6af1214d2bca9c63a79224e047650f067ba05b8b4`,
and its canonical self-digest is
`5c7ef6d72581965c456530e0b33cf21d9a98e0f731f12a89c6b0f64384d4e061`.
The unverified output file digest observed for preservation is
`5f260ccddb8d25c797812bf9c666fdeb04478a6d442f5a32ca242a7ede5176a1`.

The canonical failure is
`6803150661670be0b193b51fdd3e03c0a5fbda0232a2d9fc8927edf2abe8694a`.
Independent review
`946810043041362d1144a18685a8dc65645910050d3b59a702f029f4eafc2264`
found no remaining actionable issue after correcting the initial report
self-digest to include the production canonical trailing newline. The terminal
failure, review, receipt, and task state were committed and pushed at
`5ffaaa6be2cd145f8d0a74af2fe69724b2bd34ac`.

Before launch, the exact isolated dispatch reproduced, the complete owning
pytest file passed 27 tests, and strict OpenSpec validation passed all 84 items.
After failure, the exact wrapper was stopped only after the Python child was
absent and receipt/output publication was closed; a later process observation
found no matching r3 build process. No `verify-inventory` command ran.

## What Worked

- The r1 generated-root defect and r2 isolated-entrypoint defect were both
  repaired and preserved as terminal predecessors before r3 authority.
- The r3 request, source inventory, path preflight, approval, authorization,
  launch observation, and pre-start gate were separately reviewed and pushed.
- Receipt creation correctly consumed the logical identity before repository
  seed discovery, and atomic publication left no staging root.
- The post-receipt terminal rule prevented an apparently complete but
  independently unverified artifact from becoming a registration or training
  input.
- No native module, model, environment, game, CommunicationMod, training,
  evaluation, qualification, promotion, or gameplay operation occurred.

## Failure Analysis

`build_inventory` publishes the closed artifact and returns its full Python
mapping. The CLI entrypoint then unconditionally executes
`sys.stdout.buffer.write(canonical_json_bytes(artifact))`. That behavior is
reasonable for bounded control-plane artifacts but unsafe for a multi-gigabyte
inventory. It both attempts an oversized single stream write and forces the
outer PowerShell observer to process the full JSON even though the canonical
file is already durable.

This is a CLI result-publication defect, not evidence that the inventory bytes
are valid or invalid. The failure contract deliberately forbids running the
verifier after a failed build invocation, so r3 cannot answer that question.

## Next Gate

The next change should repair the inventory CLI before any r4 authority chain
is proposed. It should:

1. Keep `check-dispatch` canonical stdout unchanged because that artifact is
   bounded and part of the registered dispatch identity.
2. Make `build-inventory` and `verify-inventory` emit only a bounded canonical
   result containing operation, status, closed output path, receipt identity,
   inventory digest, and file size rather than the full inventory.
3. Add regressions proving stdout remains bounded for a large synthetic
   artifact and that direct Python APIs, durable output bytes, verifier
   reconstruction, and fail-closed receipt semantics remain unchanged.
4. Independently review and push the repair before defining any distinct r4
   source, request id, output root, approval, authorization, or launch
   observation.

This postmortem grants no successor invocation, registration, training, or
downstream execution authority. Fresh gameplay validation is not applicable to
this source-only terminal identity.
