# Noncombat Card-Acceptance Inventory R4 Postmortem

## Outcome

R4 built and published a valid compact v4 inventory, then failed closed at the
verification authority boundary. No verification result was accepted, no
registration was created, and parent tasks 6.2 and 6.3 remain incomplete.

## Build Evidence

- Exact `build-inventory` exited 0 after 291.3 seconds.
- The canonical inventory is 249,500 bytes, below the 64 MiB ceiling. It binds
  805 registered sources, 11,775,420 seed occurrences, 6,821 excluded seeds,
  and fixed 512 training, 128 canary, and 512 holdout cohorts.
- The bounded completion is 1,286 bytes, below the 2,048-byte ceiling.
- The immutable started receipt and inventory are tracked and pushed.

## Terminal Boundary

The first commit review reported that the generated inventory and receipt were
not yet tracked. That finding was fixed by tracking their exact bytes and by
marking the verification request non-executable until its later authority and
launch boundaries existed.

The corrected-range commit review then executed `verify-inventory` itself with
the old build launch observation, without isolated mode and before a distinct
verification authorization or fresh launch observation existed. The review
transcript did not retain a complete child exit/stdout result. This unexpected
read-only execution cannot be promoted to verified evidence, and running the
verifier again would violate the registered once-only verification boundary.
R4 is therefore terminal without registration.

## Preserved Guarantees

- The r4 inventory, receipt, build completion, request, and terminal evidence
  remain immutable and tracked.
- No r3 inventory content was read, hashed, parsed, converted, or registered.
- No native module, model, checkpoint, environment, training, evaluation,
  gameplay, CommunicationMod, OPE, qualification, or promotion ran.
- A static subagent independently reviewed the terminal artifact and reported
  no findings without executing any referenced command.

## Verification Evidence

- Owning seed-inventory and standalone-verifier tests: 101 passed in 103.66s.
- Fixed-source full gate: 5,773 passed, 18 skipped.
- Strict OpenSpec validation before closeout: 84 passed, 0 failed.
- Fresh gameplay validation: not applicable to this source-only control-plane
  change.

## Follow-Up

Before any r5 identity, make distinct verification authorization a production
CLI input and add an immutable one-shot verification execution receipt. Static
review tooling must be unable to run an eligible verifier command merely by
reading a request artifact. Only after that code-level boundary is reviewed,
tested, and pushed should a new compact-inventory successor be preregistered.
