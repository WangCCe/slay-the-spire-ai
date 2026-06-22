# Non-Combat Mismatch Stability

- Batches: baseline, candidate
- Stable high-confidence mismatches: 13
- Policy-ready stable mismatches: 6

## Stable Mismatches

- shop: shop:buy_potion:block_potion -> shop:leave (baseline=1, candidate=7, total=8, policy-candidate)
- card_reward: card_reward:skip -> card_reward:take:twin_strike (baseline=1, candidate=5, total=6, policy-candidate)
- card_reward: card_reward:take:armaments -> card_reward:take:twin_strike (baseline=1, candidate=3, total=4, policy-candidate)
- card_reward: card_reward:take:shrug_it_off -> card_reward:take:twin_strike (baseline=1, candidate=2, total=3, policy-candidate)
- card_reward: card_reward:take:uppercut -> card_reward:take:pommel_strike (baseline=1, candidate=2, total=3, policy-candidate)
- card_reward: card_reward:take:power_through -> card_reward:take:perfected_strike (baseline=1, candidate=1, total=2, policy-candidate)
- route: route:choice:1 -> route:choice:0 (baseline=32, candidate=214, total=246, diagnostic)
- route: route:choice:0 -> route:choice:1 (baseline=10, candidate=138, total=148, diagnostic)
- route: route:choice:2 -> route:choice:0 (baseline=2, candidate=29, total=31, diagnostic)
- route: route:choice:1 -> route:choice:2 (baseline=2, candidate=24, total=26, diagnostic)
- route: route:choice:2 -> route:choice:1 (baseline=2, candidate=18, total=20, diagnostic)
- route: route:choice:2 -> route:choice:3 (baseline=2, candidate=6, total=8, diagnostic)
- route: route:choice:3 -> route:choice:0 (baseline=2, candidate=4, total=6, diagnostic)
