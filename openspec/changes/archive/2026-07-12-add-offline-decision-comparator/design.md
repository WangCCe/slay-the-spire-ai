## Context
The current agent already logs many decisions and writes rich `.run` records, but not every operating decision has the same evidence quality. Card rewards and path outcomes are present in `.run` files. Shop purchases and event outcomes are present after the fact, while full shop offers, option labels, and route candidate details may require decision trace rows or explicit fixtures. Bottled AI is a local reference implementation with ordered handlers and strategy configs; the useful Phase 1 surface is its explainable shop, event, map, and card reward behavior, not its combat calculator.

## Goals
- Build a small offline comparator that works without launching Slay the Spire.
- Compare four operating-decision families in priority order: shop, event, route, card reward.
- Use local `bottled_ai` as a read-only reference and encode only the minimal Bottled-style rules needed for the samples.
- Produce a report that distinguishes exact disagreements from weak or partial-evidence differences.
- Preserve the later repair gate: no gameplay-code changes unless repeated, high-confidence, first-win-relevant differences are found.

## Non-Goals
- Do not import or vendor `bottled_ai` into the runtime agent.
- Do not replace or rewrite `spirecomm/ai/agent.py`.
- Do not train, tune, or change RL behavior.
- Do not compare combat play sequencing in Phase 1.
- Do not require a fresh gameplay batch to run the comparator.

## Data Flow
1. Load samples from one or more sources:
   - `.run` records for path, card reward, event outcome, and purchased-item summaries.
   - decision trace JSONL rows when a screen/action row contains enough context.
   - constructed fixtures for missing screen-state details such as shop offers and route candidates.
2. Normalize each input into a decision sample with category, floor, act, player/deck/relic/gold context, options, our choice, and evidence source.
3. Evaluate the sample with a Bottled-style adapter:
   - `requested_strike` card reward desired-card counts for Ironclad card rewards.
   - `requested_strike` shop purchase order: purge curses, Perfected Strike, Membership Card, purge starter cards, listed relics, listed cards.
   - `requested_strike` event overrides plus common event thresholds.
   - common map reward-to-survivability path scoring.
4. Emit comparison rows with match status, reference choice, reason, confidence, and limitations.
5. Aggregate repeated high-confidence disagreements and rank 3-5 candidate issues by frequency, confidence, and first-win relevance.

## Report Shape
The first POC report should be a Markdown file or stdout text with:
- Summary counts by category and evidence quality.
- A table of comparison rows: category, source, floor, our choice, Bottled-style choice, match, confidence, reason.
- A ranked "Most Worth Fixing" section with 3-5 issues or fewer if the evidence does not support that many.
- A "No Fix Yet" section when differences are weak, isolated, or unrelated to the first-win objective.

## Risks And Mitigations
- Risk: `.run` records lack offered shop cards/relic prices. Mitigation: mark those rows as partial evidence and use fixtures or trace rows for high-confidence shop comparisons.
- Risk: Bottled strategy names and card IDs differ from local spirecomm objects. Mitigation: normalize names with upgrade-stripping and compact identifiers, and show the normalized keys in report details.
- Risk: route scoring needs map topology, not just `path_taken`. Mitigation: use route fixtures for full route comparisons and reserve `.run` path summaries for coarse outcome analysis.
- Risk: reference behavior can be overfit to one Bottled strategy. Mitigation: Phase 1 defaults to Ironclad `REQUESTED_STRIKE` and labels that assumption in every report.

## Verification
- Add focused unit tests for sample normalization, each adapter, confidence classification, and report ranking.
- Run the POC against at least one local `.run` record plus constructed fixtures that cover shop, event, route, and card reward.
- Do not claim the goal is complete until a report is generated locally and the top 3-5 decision issues are listed or explicitly fewer are justified by evidence.

## Investigation Notes
- Current local decision surfaces are concentrated in `spirecomm/ai/agent.py`: `_choose_event_option`, the `SHOP_SCREEN` branch in `handle_screen`, `choose_card_reward`, and `generate_map_route`.
- Existing local tests already cover the same decision families: `tests/test_shop_screen_guards.py`, `tests/test_event_choice_guard.py`, `tests/test_map_routing_safety.py`, `tests/test_ironclad_card_reward_guards.py`, and `tests/test_decision_trace.py`.
- Local sample data exists without launching gameplay: recent Ironclad `.run` records under `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD`, `ai_decision_trace_clean.jsonl`, `ai_debug.log`, and constructed test fixtures.
- The current clean decision trace is large and should be read with bounded tail/window filters, not loaded wholesale.
- Bottled Ironclad reference behavior is best represented by `rs/ai/requested_strike/config.py`, `rs/ai/requested_strike/handlers/shop_purchase_handler.py`, `rs/ai/requested_strike/handlers/event_handler.py`, `rs/common/handlers/card_reward/common_card_reward_handler.py`, and `rs/common/handlers/common_map_handler.py`.
- `.run` records can provide real choices for card rewards, events, purchases, and paths, but high-confidence shop and route comparisons need either decision trace rows with screen context or explicit fixtures with full offers and map candidates.
