# improve-combat-potion-usage

## Summary
Enhance the AI's potion usage logic to use potions strategically during difficult combat situations, not just in boss fights. The current implementation only considers potions in boss rooms (line 82-85 in agent.py), which leads to unnecessary deaths in elite fights and regular encounters when potions could turn the tide.

## Motivation
Currently, the AI hoards potions and rarely uses them outside of boss fights. This causes avoidable deaths in situations where a damage potion could kill a dangerous elite, a block potion could prevent lethal damage, or a healing potion could restore critical HP. Potions should be viewed as combat resources to be deployed when they provide high value, not items to be saved exclusively for bosses.

## Proposed Solution
Integrate potion usage into the OptimizedAgent's beam search combat planning, allowing the AI to evaluate potions as potential actions alongside cards. This will enable:

1. **Intelligent potion timing**: Use potions when beam search indicates they improve the outcome score
2. **Potion synergy detection**: Evaluate potions in the context of card sequences (e.g., use Strength Potion before playing multiple attacks)
3. **Danger-based potion usage**: Automatically use potions when the combat danger level is high, even in non-boss fights
4. **Lethal prevention**: Use defensive/healing potions when expected to die otherwise

## Scope
The change affects:
- `spirecomm/ai/agent.py`: Remove the boss-only restriction and improve danger evaluation
- `spirecomm/ai/heuristics/simulation.py`: Add potion actions to beam search expansion
- New capability: `combat-potion-usage` (spec delta)

## Alternatives Considered
1. **Simple threshold-based**: Use potions when HP/damage thresholds are met
   - *Pros*: Simpler implementation
   - *Cons*: Less intelligent, doesn't consider card synergies

2. **Keep current approach**: Only use potions in boss fights
   - *Pros*: Minimal changes
   - *Cons*: Doesn't address the problem, AI continues dying with unused potions

3. **Potion usage in beam search** (chosen)
   - *Pros*: Most intelligent, considers synergies and timing
   - *Cons*: More complex, requires integration with simulation system

## Impact
- **Positive**: Reduced deaths in difficult fights, better potion value extraction
- **Risk**: Over-use of potions in easy fights (mitigated by danger thresholds)
- **Testability**: Can measure win rate improvement and potion usage frequency

## Related Changes
- Builds on existing `ai-combat` spec (beam search infrastructure)
- Complements the danger evaluation logic already in OptimizedAgent

## Dependencies
None - this is a self-contained enhancement

## Open Questions
1. Should we limit potions to 1 per turn to prevent spamming multiple potions?
   - **Answer**: Yes, limit to 1 potion action per beam search sequence (Conservative)
2. Should certain "premium" potions (e.g., Ghost in a Jar) still be reserved for elites/bosses?
   - **Answer**: Let beam search decide, but add value bonus for rare potions
