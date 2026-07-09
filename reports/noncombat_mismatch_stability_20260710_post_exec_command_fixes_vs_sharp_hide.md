# Non-Combat Mismatch Stability

- Batches: baseline, candidate
- Stable high-confidence mismatches: 6
- Policy-ready stable mismatches: 1

## Stable Mismatches

- shop: shop:buy_potion:block_potion -> shop:leave (baseline=1, candidate=1, matched_outcomes=baseline=1, candidate=1, total=2, policy-candidate)
- card_reward: card_reward:skip -> card_reward:take:twin_strike (baseline=1, candidate=1, matched_outcomes=baseline=0, candidate=0, total=2, diagnostic)
- route: route:choice:1 -> route:choice:0 (baseline=36, candidate=20, matched_outcomes=baseline=10, candidate=14, total=56, diagnostic)
- route: route:choice:0 -> route:choice:1 (baseline=6, candidate=22, matched_outcomes=baseline=6, candidate=14, total=28, diagnostic)
- route: route:choice:0 -> route:choice:2 (baseline=7, candidate=2, matched_outcomes=baseline=0, candidate=0, total=9, diagnostic)
- route: route:choice:1 -> route:choice:2 (baseline=3, candidate=2, matched_outcomes=baseline=2, candidate=0, total=5, diagnostic)
