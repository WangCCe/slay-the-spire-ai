# Guard-intervention action audit

The replay action binding is working. Of 3,015 positive-energy replay states,
2,941 store a non-EndTurn executed action and only 74 store EndTurn.

The learned candidate nevertheless chooses EndTurn greedily on 2,152 of those
positive-energy states, versus 1,832 for the parent. It creates 331 states where
the parent chose a non-EndTurn action, the candidate changed to EndTurn, and the
stored executed action was non-EndTurn in every case. Candidate agreement with
the stored action also falls from `24.76%` for the parent to `22.63%`.

This rules out missing guard-action rebinding as the primary failure. The
current TD objective learns only the selected action value, while the anchor
imitates the parent rather than the guard-executed action. A small direct
imitation term on positive-energy, non-EndTurn executed actions is the next
bounded hypothesis to test on fixed replay before changing live training.
