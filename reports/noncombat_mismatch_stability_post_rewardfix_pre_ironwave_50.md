# Non-Combat Mismatch Stability

- Batches: baseline, candidate
- Stable high-confidence mismatches: 11
- Policy-ready stable mismatches: 5

## Stable Mismatches

- shop: shop:buy_potion:block_potion -> shop:leave (baseline=1, candidate=7, total=8, policy-candidate)
- card_reward: card_reward:skip -> card_reward:take:twin_strike (baseline=1, candidate=3, total=4, policy-candidate)
- card_reward: card_reward:take:anger -> card_reward:take:flame_barrier (baseline=1, candidate=1, total=2, policy-candidate)
- card_reward: card_reward:take:iron_wave -> card_reward:take:twin_strike (baseline=1, candidate=1, total=2, policy-candidate)
- card_reward: card_reward:take:shrug_it_off -> card_reward:take:twin_strike (baseline=1, candidate=1, total=2, policy-candidate)
- route: route:choice:1 -> route:choice:0 (baseline=32, candidate=204, total=236, diagnostic)
- route: route:choice:0 -> route:choice:1 (baseline=10, candidate=154, total=164, diagnostic)
- route: route:choice:2 -> route:choice:1 (baseline=2, candidate=24, total=26, diagnostic)
- route: route:choice:1 -> route:choice:2 (baseline=2, candidate=19, total=21, diagnostic)
- route: route:choice:2 -> route:choice:0 (baseline=2, candidate=12, total=14, diagnostic)
- route: route:choice:3 -> route:choice:0 (baseline=2, candidate=2, total=4, diagnostic)
