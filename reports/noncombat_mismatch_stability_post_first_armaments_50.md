# Non-Combat Mismatch Stability

- Batches: baseline, candidate
- Stable high-confidence mismatches: 12
- Policy-ready stable mismatches: 5

## Stable Mismatches

- shop: shop:buy_potion:block_potion -> shop:leave (baseline=1, candidate=5, total=6, policy-candidate)
- card_reward: card_reward:take:armaments -> card_reward:take:twin_strike (baseline=1, candidate=1, total=2, policy-candidate)
- card_reward: card_reward:take:iron_wave -> card_reward:take:twin_strike (baseline=1, candidate=1, total=2, policy-candidate)
- card_reward: card_reward:take:shrug_it_off -> card_reward:take:twin_strike (baseline=1, candidate=1, total=2, policy-candidate)
- card_reward: card_reward:take:uppercut -> card_reward:take:pommel_strike (baseline=1, candidate=1, total=2, policy-candidate)
- route: route:choice:1 -> route:choice:0 (baseline=32, candidate=185, total=217, diagnostic)
- route: route:choice:0 -> route:choice:1 (baseline=10, candidate=135, total=145, diagnostic)
- route: route:choice:2 -> route:choice:0 (baseline=2, candidate=24, total=26, diagnostic)
- route: route:choice:2 -> route:choice:1 (baseline=2, candidate=12, total=14, diagnostic)
- route: route:choice:1 -> route:choice:2 (baseline=2, candidate=9, total=11, diagnostic)
- route: route:choice:2 -> route:choice:3 (baseline=2, candidate=8, total=10, diagnostic)
- route: route:choice:3 -> route:choice:0 (baseline=2, candidate=6, total=8, diagnostic)
