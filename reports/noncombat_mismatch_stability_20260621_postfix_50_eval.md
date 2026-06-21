# Non-Combat Mismatch Stability

- Batches: baseline, candidate
- Stable high-confidence mismatches: 6
- Policy-ready stable mismatches: 3

## Stable Mismatches

- shop: shop:purge:strike -> shop:buy_card:perfected_strike (baseline=1, candidate=3, total=4, policy-candidate)
- shop: shop:leave -> shop:buy_card:perfected_strike (baseline=1, candidate=2, total=3, policy-candidate)
- card_reward: card_reward:take:anger -> card_reward:take:dropkick (baseline=1, candidate=1, total=2, policy-candidate)
- route: route:choice:0 -> route:choice:1 (baseline=16, candidate=28, total=44, diagnostic)
- route: route:choice:1 -> route:choice:0 (baseline=22, candidate=20, total=42, diagnostic)
- route: route:choice:1 -> route:choice:2 (baseline=6, candidate=2, total=8, diagnostic)
