# Non-Combat Mismatch Stability

- Batches: baseline, candidate
- Stable high-confidence mismatches: 10
- Policy-ready stable mismatches: 4

## Stable Mismatches

- shop: shop:buy_potion:block_potion -> shop:leave (baseline=1, candidate=7, total=8, policy-candidate)
- card_reward: card_reward:take:iron_wave -> card_reward:take:twin_strike (baseline=1, candidate=2, total=3, policy-candidate)
- card_reward: card_reward:skip -> card_reward:take:twin_strike (baseline=1, candidate=1, total=2, policy-candidate)
- card_reward: card_reward:take:anger -> card_reward:take:flame_barrier (baseline=1, candidate=1, total=2, policy-candidate)
- route: route:choice:1 -> route:choice:0 (baseline=32, candidate=205, total=237, diagnostic)
- route: route:choice:0 -> route:choice:1 (baseline=10, candidate=113, total=123, diagnostic)
- route: route:choice:2 -> route:choice:0 (baseline=2, candidate=14, total=16, diagnostic)
- route: route:choice:2 -> route:choice:1 (baseline=2, candidate=14, total=16, diagnostic)
- route: route:choice:1 -> route:choice:2 (baseline=2, candidate=8, total=10, diagnostic)
- route: route:choice:3 -> route:choice:0 (baseline=2, candidate=6, total=8, diagnostic)
