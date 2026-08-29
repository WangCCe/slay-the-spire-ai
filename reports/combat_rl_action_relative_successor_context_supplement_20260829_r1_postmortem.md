# Successor context supplement postmortem

## Decision

The registered supplement completed successfully, but the merged fresh corpus
did not pass the unchanged real-context support gate. The experiment therefore
closed before optimizer construction, model fitting, training, or gameplay.

The published manifest contains eight artifacts; every recorded size and
SHA-256 hash matches. Merged corpus identities, partition seed isolation, and
round-trip validation also pass.

## Result

- Merged train support passes every condition: coverage `0.940664`, ESS
  `871.403`, floor-23-27 coverage `0.852194`, and floor-28-34 coverage `1.0`.
- Merged fresh support fails three conditions: coverage `0.864281 < 0.90`,
  floor-23-27 coverage `0.789838 < 0.80`, and weighted HP SMD
  `0.217938 > 0.20`.
- Fresh ESS `770.214`, floor-28-34 coverage `0.761350`, concentration,
  weighted floor/potion/relic balance, legality, provenance, and seed isolation
  all pass.
- The formal battle-10 slice initialized 711 of 1,536 profiles and retained
  1,215 source states. The historical 2,048-profile proxy block initialized
  1,042 profiles and retained 1,798 rows.

## Projection error

The historical proxy block contained eight rows in the rare context cell
`floor_23_27|p0|r3|h0`; the formal battle-10 block contained none. That cell
represents 27 of the 7,685 bound real replay rows and accounts for the entire
drop from projected floor-23-27 coverage `0.852194` to formal coverage
`0.789838`.

Across all real cells absent from the r2 base, historical battle-10 support but
not formal battle-10 support represented `0.030189` of real mass. Formal-only
support represented just `0.001171`. The five-fold projection split one
historical seed block, so it measured within-block stability but not
between-block rare-cell drift. Its apparent margin was therefore not a valid
formal-cohort guarantee.

## Consequence

Do not fit on this corpus and do not repeat the same supplement recipe with a
new seed block. Before collecting more successor rows, audit whether the target
distribution should be all r14/r15 combat transitions or only real
action-relative guard-replacement opportunities. The simulator corpus retains
only the latter class, while the current support target includes every replay
transition. Existing live-shadow traces should be used first so this audit does
not require new gameplay.
