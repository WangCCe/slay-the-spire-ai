# Combat LightSTS replay target interaction audit

## Decision

The next capability should add opt-in frozen-parent deployment-guard bootstrap
actions before another candidate fit. Running the existing r16 guarded behavior
with the existing n-step target would not close the identified mismatch because
that target still bootstraps through the parent's raw maximum-Q action.

## Current evidence

- The fresh optimizer-dose cohort used production-r16 guarded behavior and
  recorded 21,241 guard replacements among 51,560 accepted transitions (41.2%).
- Reducing training from 256 to 64 or 128 updates reduced parameter drift but
  did not improve held-out policy gates. The 256-update arm was strongest on
  reward and still failed HP, rejecting optimizer dose as the primary cause.
- One-step TD ranked above complete discounted returns, but neither improved
  production r16.
- Removing the raw-parent anchor materially worsened reward and victories.
- Changing replacement-row anchor labels to the executed proxy action was
  strongly negative on a fresh cohort.
- Parent card, EndTurn, and top-action margin objective variants did not produce
  a fresh eligible successor.
- Collision-free encounter identity gave a small direct gain but did not pass
  the production-r16 successor gate.
- The prior frozen-parent n-step study used an older r4 parent and uniform
  non-EndTurn behavior. Its n3 arm improved aggregate reward over one-step but
  regressed early and late strata and was ineligible.

## Located interaction

Guarded replay collection and target construction evaluate different policies:

| Stage | Current policy/action source |
| --- | --- |
| Behavior parent branch | Frozen parent transformed by deployment guard |
| Behavior exploration branch | Seeded exploratory non-EndTurn action |
| Replay action | Action actually executed |
| Parent anchor | Frozen-parent raw greedy action by default |
| One-step bootstrap action | Candidate online-network raw legal argmax |
| One-step bootstrap value | Target-network Q at that raw argmax |
| Frozen-parent n-step bootstrap | Frozen-parent raw maximum legal Q |
| Deployment evaluation | Candidate raw action transformed by deployment guard |

The implemented proxy-aware anchor ablation changed only the current-row anchor
label. It did not change either one-step or n-step next-state bootstrap actions.
Likewise, guarded behavior changed collected actions but not the target policy.

## Required boundary

The smallest coherent change is simulator-only:

1. Compute the deterministic frozen-parent guarded action at every collected
   state independently of epsilon exploration.
2. Align each nonterminal n-step bootstrap state to that stored target action.
3. Gather immutable parent Q at the aligned guarded action instead of raw max Q.
4. Validate action legality before replay insertion and bind replacement and
   raw-max Q-gap telemetry.
5. Preserve raw-greedy bootstrap as the default and require a separate fresh
   registration before any fit.

This does not authorize gameplay, CommunicationMod, production checkpoint
changes, candidate fitting, packaging, qualification, or promotion.
