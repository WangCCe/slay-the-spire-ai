## Context

The first encounter-aware experiment used SHA-256 modulo 64. Its model width
and parent migration worked, but 42 encountered identities collapsed to 31
buckets. LightSTS exposes 63 valid names in `MonsterEncounters.h`, making a
collision-free mapping possible in the existing 64 columns.

## Goals / Non-Goals

**Goals:**

- Preserve the 392-dimensional network and exact r4 parent migration.
- Map every canonical LightSTS encounter to a unique stable column.
- Fail on vocabulary drift instead of silently hashing an unknown name.
- Run one fresh same-budget comparison against r4.

**Non-Goals:**

- Tune the hash experiment or compare several vocabulary variants.
- Add live encounter mapping or make the candidate production-compatible.
- Change replay, reward, anchor, optimizer, or cohort size.

## Decisions

1. Add encoding mode `monster-encounter-enum-v1`. Bucket 0 is reserved and the
   63 names from LightSTS `monsterEncounterEnumNames` map to 1..63 in source
   order.
2. Store the tuple in the source-bound runner and bind its canonical SHA-256 in
   reports/checkpoints. Native tests verify representative identities and all
   63 assignments are unique.
3. Keep the existing hash mode as the compatibility default. Enum mode requires
   exactly 64 buckets and rejects unknown encounter names.
4. Reuse zero-column parent migration unchanged because input width is still
   328+64. The fresh experiment changes only feature assignment and randomness.

## Risks / Trade-offs

- The copied enum can drift from LightSTS. -> Bind simulator commit and
  vocabulary hash; reject unknown names and test the source-order contract.
- Collision removal may still not fix delayed credit assignment. -> Keep the
  existing index 9 guardrails and stop this representation line on failure.
- Live names may differ. -> Retain false production compatibility and no live
  transfer authority.
