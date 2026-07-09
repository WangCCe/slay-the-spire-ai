# Mind Bloom Low-HP No-Heal Guard - 2026-07-10

- Source batch: post-Preserved Insect fresh eval, 24 completed AI-marked A0 Ironclad runs, no victories.
- Selected live evidence: `1783611889.run` reached floor 44 and died to Transient after taking `MindBloom:Upgrade` on floor 38 at `21/42` HP. The decision trace shows the event selected `I am Awake`, immediately gained `Mark of the Bloom`, then later reached a floor-40 rest that could not heal.
- Root cause: the low-HP Mind Bloom guard only avoided the immediate `I am War` boss fight. It preferred `I am Awake`, which prevents all future healing and can turn a low-HP Act 3 path with upcoming rests into a terminal state.
- Fix: low-HP Mind Bloom now prefers `I am Rich` before `I am Awake`; the healthy-HP branch still prefers `I am War`.
- Regression: `test_mind_bloom_takes_gold_instead_of_no_heal_relic_when_low_hp` and `test_mind_bloom_avoids_mark_of_bloom_after_council_of_ghosts_hp_loss` failed red by selecting index 1 and passed after the policy change.
- Verification: targeted Mind Bloom tests passed (`3 passed`), `tests/test_event_choice_guard.py` passed (`48 passed`), and full pytest passed (`2234 passed in 82.51s`).
- Next check: rerun a bounded fresh eval from this guard and watch whether deep Act 3 runs still die from low-HP rest lockout or shift back to route/combat survival issues.
