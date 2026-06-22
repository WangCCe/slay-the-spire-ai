# Non-Combat Mismatch Stability

- Batches: baseline, candidate
- Stable high-confidence mismatches: 10
- Policy-ready stable mismatches: 4

## Stable Mismatches

- shop: shop:buy_potion:block_potion -> shop:leave (baseline=1, candidate=4, total=5, policy-candidate)
- card_reward: card_reward:skip -> card_reward:take:twin_strike (baseline=1, candidate=3, total=4, policy-candidate)
- card_reward: card_reward:take:armaments -> card_reward:take:pommel_strike (baseline=1, candidate=3, total=4, policy-candidate)
- card_reward: card_reward:take:shrug_it_off -> card_reward:take:twin_strike (baseline=1, candidate=2, total=3, policy-candidate)
- route: route:choice:1 -> route:choice:0 (baseline=32, candidate=177, total=209, diagnostic)
- route: route:choice:0 -> route:choice:1 (baseline=10, candidate=112, total=122, diagnostic)
- route: route:choice:2 -> route:choice:1 (baseline=2, candidate=26, total=28, diagnostic)
- route: route:choice:2 -> route:choice:0 (baseline=2, candidate=14, total=16, diagnostic)
- route: route:choice:1 -> route:choice:2 (baseline=2, candidate=11, total=13, diagnostic)
- route: route:choice:3 -> route:choice:0 (baseline=2, candidate=2, total=4, diagnostic)
