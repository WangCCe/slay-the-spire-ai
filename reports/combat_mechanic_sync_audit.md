# Combat Mechanic Sync Audit

This report tracks mechanics that were proven during sim divergence work and
may also need to be reflected in live combat estimators. The goal is not to
make `sim_divergence.py` a shared runtime dependency; it is to prevent separate
decision-time estimators from preserving mechanics that live evidence has
already disproved.

## Estimator Surfaces

- `spirecomm/ai/sim_divergence.py`: diagnostic one-action oracle.
- `spirecomm/ai/heuristics/combat_ending.py`: lethal detection and lethal
  sequence construction.
- `spirecomm/ai/heuristics/simulation.py`: beam-search combat simulation,
  fast scoring, and sequence scoring.
- `spirecomm/ai/heuristics/ironclad_combat.py`: target choice and fallback
  combat planning.
- RL guard/reward code: action vetoes and reward estimates that may duplicate
  card or combat outcome estimates.

## Sync Rules

- Port deterministic mechanics that affect live decision estimates.
- Do not blindly port trace-settlement boundaries that only suppress diagnostic
  false positives, such as delayed CardSelect animation fields, unless the
  decision estimator also predicts that intermediate state.
- Each port should have its own focused regression in the owning estimator's
  test file before implementation.

## Confirmed Sync Work

- 2026-06-07: `CombatEndingDetector` now uses the same confirmed target-side
  attack modifier shape as the divergence oracle for:
  - player Weak plus target Vulnerable combined before final integer
    truncation (`9/8`);
  - Paper Phrog target Vulnerable (`7/4`);
  - Paper Phrog plus player Weak and target Vulnerable (`21/16`).
- 2026-06-07: `FastCombatSimulator` and the same-file no-simulation attack
  estimate now share that target-side attack modifier shape:
  - `simulate_card_play` attack branches apply player Weak plus target
    Vulnerable with one final truncation;
  - Paper Phrog increases target Vulnerable attack damage to `7/4`;
  - fallback attack damage scoring uses the same helper before Slow and hit-count
    expansion.
- 2026-06-07: `IroncladCombatPlanner` fallback attack damage estimates now
  count upgraded static attack damage when parsed card data only exposes the
  base value. This keeps Bash follow-up checks and non-clone fallback scoring
  from underestimating cards such as Headbutt+.
- 2026-06-07: `CombatRLAgent` survival guards now include Decay in end-turn
  status HP loss alongside Burn. Guard takeover decisions treat that HP loss as
  unblocked when deciding whether to replace an RL attack with a defensive card.
- 2026-06-07: `TimingAwareCombatPlanner` target-specific and scalar timing
  damage estimates now use the confirmed target-side attack modifier shape:
  - player Weak plus target Vulnerable is combined before final integer
    truncation (`9/8`);
  - Paper Phrog target Vulnerable uses `7/4`;
  - Paper Phrog plus player Weak and target Vulnerable uses `21/16`.

## Backlog

- Add a streaming `sim_divergence_trace_clean.jsonl` analyzer so large clean
  traces can be summarized by cutoff without PowerShell full-file JSON parsing.
- Expand this report into a compact coverage matrix from divergence rounds
  105-118: rows as mechanics, columns as estimator surfaces.
- Audit high-impact confirmed mechanics across live estimators:
  - Whirlwind per-energy hits, per-hit rounding, and Malleable interactions.
  - Paper Phrog, Pen Nib, Weak/Vulnerable, Strength, and upgraded attack stats.
  - Mind Blast/deck-count and other dynamic base damage.
  - Havoc top-card effects, random-target boundaries, and Feel No Pain block.
  - End-turn statuses such as Burn and Decay.
  - Monster lifecycle boundaries such as Slime split and Darkling revive.
  - Combat-exit boundaries such as Smoke Bomb and Looter escape.
