## Context

The rejected warm-start successor is a meaningful learned direction rather than an independent random candidate: it improves one battle stratum substantially while slightly regressing others. Existing production-checkpoint interpolation tooling assumes schema-2 replay-bearing checkpoints and cannot safely consume schema-0 LightSTS artifacts.

## Goals / Non-Goals

**Goals:**

- Construct exact linear parameter interpolations between two bound schema-0 simulator checkpoints.
- Publish each interpolation as a valid simulator-only candidate accepted by the existing frozen comparator.
- Make construction deterministic, atomic, hash-bound, and independently inspectable.

**Non-Goals:**

- Fit or tune model parameters.
- Interpolate optimizer, replay, target-network, or production checkpoint state.
- Select an alpha inside the construction utility.
- Grant live transfer or promotion authority.

## Decisions

1. Use a dedicated LightSTS utility rather than weakening production checkpoint interpolation validation. The two artifact schemas have intentionally different authority and contents.
2. Require expected SHA-256 values for both inputs and reuse frozen-comparator checkpoint validation. This rejects production-compatible and malformed inputs before output creation.
3. Require exact key, shape, and dtype agreement. Every state value must be floating point; the output is `parent + alpha * (candidate - parent)` cast back to the source dtype.
4. Allow only unique alphas strictly inside `(0, 1)`. Parent and full successor remain their original immutable checkpoints.
5. Preserve schema-0 `simulator_training_smoke`, `production_compatible=false`, and source-only authority. Metadata binds both input file and parameter hashes, alpha, output parameter hash, and source commit.
6. The generator does not rank or select. The existing frozen comparator evaluates all preregistered candidates on a fresh cohort; any selected alpha requires a second fresh confirmation.

## Risks / Trade-offs

- [Linear interpolation may not preserve behavior monotonically] -> Evaluate every fixed alpha rather than infer from parameter distance.
- [Multiple-alpha development evaluation creates selection bias] -> Permit at most one selected alpha and require an untouched confirmation cohort.
- [Generated files could be mistaken for production weights] -> Keep simulator checkpoint kind, explicit false authority, and production incompatibility.
- [Interpolation may hide incompatible model structures] -> Validate exact structures and fail before creating the output directory.

