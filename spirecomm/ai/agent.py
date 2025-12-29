import time
import random

from spirecomm.spire.game import Game
from spirecomm.spire.character import Intent, PlayerClass
import spirecomm.spire.card
from spirecomm.spire.screen import RestOption
from spirecomm.communication.action import *
from spirecomm.ai.priorities import *

# Import optimized AI components
try:
    from spirecomm.ai.decision.base import DecisionContext
    from spirecomm.ai.heuristics.card import SynergyCardEvaluator
    from spirecomm.ai.heuristics.simulation import HeuristicCombatPlanner
    from spirecomm.ai.heuristics.deck import DeckAnalyzer
    OPTIMIZED_AI_AVAILABLE = True
except ImportError:
    OPTIMIZED_AI_AVAILABLE = False

# Import tracker separately (always available, no dependencies)
try:
    from spirecomm.ai.tracker import GameTracker
except ImportError:
    GameTracker = None



class SimpleAgent:

    def __init__(self, chosen_class=PlayerClass.THE_SILENT):
        self.game = Game()
        self.errors = 0
        self.choose_good_card = False
        self.skipped_cards = False
        self.visited_shop = False
        self.map_route = []
        self.chosen_class = chosen_class
        self.priorities = Priority()
        self.change_class(chosen_class)

    def change_class(self, new_class):
        self.chosen_class = new_class
        if self.chosen_class == PlayerClass.THE_SILENT:
            self.priorities = SilentPriority()
        elif self.chosen_class == PlayerClass.IRONCLAD:
            self.priorities = IroncladPriority()
        elif self.chosen_class == PlayerClass.DEFECT:
            self.priorities = DefectPowerPriority()
        else:
            self.priorities = random.choice(list(PlayerClass))

    def handle_error(self, error):
        raise Exception(error)

    def get_next_action_in_game(self, game_state):
        self.game = game_state
        #time.sleep(0.07)
        try:
            if self.game.choice_available:
                return self.handle_screen()
            if self.game.proceed_available:
                return ProceedAction()
            if self.game.play_available:
                if self.game.room_type == "MonsterRoomBoss" and len(self.game.get_real_potions()) > 0:
                    potion_action = self.use_next_potion()
                    if potion_action is not None:
                        return potion_action
                return self.get_play_card_action()
            if self.game.end_available:
                return EndTurnAction()
            if self.game.cancel_available:
                return CancelAction()
        except Exception as e:
            # Fallback to safe action on error
            # Use stderr for error output to avoid interfering with Communication Mod
            import sys
            print(f"Error in get_next_action_in_game: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            if self.game.end_available:
                return EndTurnAction()
            return ProceedAction()

    def get_next_action_out_of_game(self):
        return StartGameAction(self.chosen_class)

    def is_monster_attacking(self):
        for monster in self.game.monsters:
            if monster.intent.is_attack() or monster.intent == Intent.NONE:
                return True
        return False

    def get_incoming_damage(self):
        incoming_damage = 0
        for monster in self.game.monsters:
            if not monster.is_gone and not monster.half_dead:
                if monster.move_adjusted_damage is not None:
                    incoming_damage += monster.move_adjusted_damage * monster.move_hits
                elif monster.intent == Intent.NONE:
                    incoming_damage += 5 * self.game.act
        return incoming_damage

    def get_low_hp_target(self):
        available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
        best_monster = min(available_monsters, key=lambda x: x.current_hp)
        return best_monster

    def get_high_hp_target(self):
        available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
        best_monster = max(available_monsters, key=lambda x: x.current_hp)
        return best_monster

    def many_monsters_alive(self):
        available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
        return len(available_monsters) > 1

    def get_play_card_action(self):
        playable_cards = [card for card in self.game.hand if card.is_playable]
        zero_cost_cards = [card for card in playable_cards if card.cost == 0]
        zero_cost_attacks = [card for card in zero_cost_cards if card.type == spirecomm.spire.card.CardType.ATTACK]
        zero_cost_non_attacks = [card for card in zero_cost_cards if card.type != spirecomm.spire.card.CardType.ATTACK]
        nonzero_cost_cards = [card for card in playable_cards if card.cost != 0]
        aoe_cards = [card for card in playable_cards if self.priorities.is_card_aoe(card)]
        if self.game.player.block > self.get_incoming_damage() - (self.game.act + 4):
            offensive_cards = [card for card in nonzero_cost_cards if not self.priorities.is_card_defensive(card)]
            if len(offensive_cards) > 0:
                nonzero_cost_cards = offensive_cards
            else:
                nonzero_cost_cards = [card for card in nonzero_cost_cards if not card.exhausts]
        if len(playable_cards) == 0:
            return EndTurnAction()
        if len(zero_cost_non_attacks) > 0:
            card_to_play = self.priorities.get_best_card_to_play(zero_cost_non_attacks)
        elif len(nonzero_cost_cards) > 0:
            card_to_play = self.priorities.get_best_card_to_play(nonzero_cost_cards)
            if len(aoe_cards) > 0 and self.many_monsters_alive() and card_to_play.type == spirecomm.spire.card.CardType.ATTACK:
                card_to_play = self.priorities.get_best_card_to_play(aoe_cards)
        elif len(zero_cost_attacks) > 0:
            card_to_play = self.priorities.get_best_card_to_play(zero_cost_attacks)
        else:
            # This shouldn't happen!
            return EndTurnAction()
        if card_to_play.has_target:
            available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
            if len(available_monsters) == 0:
                return EndTurnAction()
            if card_to_play.type == spirecomm.spire.card.CardType.ATTACK:
                target = self.get_low_hp_target()
            else:
                target = self.get_high_hp_target()
            return PlayCardAction(card=card_to_play, target_monster=target)
        else:
            return PlayCardAction(card=card_to_play)

    def use_next_potion(self):
        for potion in self.game.get_real_potions():
            if potion.can_use:
                if potion.requires_target:
                    return PotionAction(True, potion=potion, target_monster=self.get_low_hp_target())
                else:
                    return PotionAction(True, potion=potion)

    def handle_screen(self):
        if self.game.screen_type == ScreenType.EVENT:
            if self.game.screen.event_id in ["Vampires", "Masked Bandits", "Knowing Skull", "Ghosts", "Liars Game", "Golden Idol", "Drug Dealer", "The Library"]:
                return ChooseAction(len(self.game.screen.options) - 1)
            else:
                return ChooseAction(0)
        elif self.game.screen_type == ScreenType.CHEST:
            return OpenChestAction()
        elif self.game.screen_type == ScreenType.SHOP_ROOM:
            if not self.visited_shop:
                self.visited_shop = True
                return ChooseShopkeeperAction()
            else:
                self.visited_shop = False
                return ProceedAction()
        elif self.game.screen_type == ScreenType.REST:
            return self.choose_rest_option()
        elif self.game.screen_type == ScreenType.CARD_REWARD:
            return self.choose_card_reward()
        elif self.game.screen_type == ScreenType.COMBAT_REWARD:
            import sys
            rewards = self.game.screen.rewards if hasattr(self.game.screen, 'rewards') else []
            sys.stderr.write(f"[COMBAT_REWARD] Floor {self.game.floor if hasattr(self.game, 'floor') else '?'}: {len(rewards)} rewards, skipped_cards={self.skipped_cards}\n")

            for i, reward_item in enumerate(rewards):
                skip_potion = reward_item.reward_type == RewardType.POTION and self.game.are_potions_full()
                skip_card = reward_item.reward_type == RewardType.CARD and self.skipped_cards
                sys.stderr.write(f"  [{i}] type={reward_item.reward_type}, skip_potion={skip_potion}, skip_card={skip_card}\n")

            for reward_item in rewards:
                if reward_item.reward_type == RewardType.POTION and self.game.are_potions_full():
                    continue
                elif reward_item.reward_type == RewardType.CARD and self.skipped_cards:
                    continue
                else:
                    sys.stderr.write(f"[COMBAT_REWARD] Taking reward: {reward_item.reward_type}\n")
                    return CombatRewardAction(reward_item)
            sys.stderr.write(f"[COMBAT_REWARD] Proceeding (all rewards skipped)\n")
            self.skipped_cards = False
            return ProceedAction()
        elif self.game.screen_type == ScreenType.MAP:
            return self.make_map_choice()
        elif self.game.screen_type == ScreenType.BOSS_REWARD:
            relics = self.game.screen.relics
            best_boss_relic = self.priorities.get_best_boss_relic(relics)
            return BossRewardAction(best_boss_relic)
        elif self.game.screen_type == ScreenType.SHOP_SCREEN:
            # Smart shop decision making
            gold = self.game.gold
            screen = self.game.screen
            
            # Calculate deck stats for better decision making
            deck_size = len(self.game.deck) if hasattr(self.game, 'deck') else 0
            
            # Priority 1: Purge (card removal) if needed and affordable
            purge_cost = screen.purge_cost if screen.purge_available else float('inf')
            if screen.purge_available and gold >= purge_cost:
                # Only purge if deck is large enough or has low-value cards
                if deck_size >= 15:
                    # Count bad cards that should be removed
                    bad_cards = [c for c in self.game.deck if c.card_id in ['Strike_R', 'Defend_R', 'Bash']]
                    if len(bad_cards) >= 2:
                        return ChooseAction(name="purge")
            
            # Priority 2: Buy cards that are good for the deck
            if hasattr(self.priorities, 'get_sorted_cards'):
                # Get sorted cards by priority
                sorted_cards = self.priorities.get_sorted_cards(screen.cards)
                for card in sorted_cards:
                    # Only buy if affordable and not skipping
                    if gold >= card.price and not self.priorities.should_skip(card):
                        # Check if we can afford it after considering purge
                        if not screen.purge_available or gold - card.price >= purge_cost:
                            return BuyCardAction(card)
            else:
                # Fallback to original logic
                for card in screen.cards:
                    if gold >= card.price and not self.priorities.should_skip(card):
                        return BuyCardAction(card)
            
            # Priority 3: Buy useful relics (consider price and value)
            # Only buy relics if we have enough gold left (keep some for purge/cards if needed)
            for relic in screen.relics:
                # Skip expensive relics that might prevent more important purchases
                if gold >= relic.price and relic.price <= gold * 0.7:  # Don't spend all gold on relics
                    # Prioritize useful relics for Ironclad
                    useful_relics = ['Burning Blood', 'Barricade', 'Demon Form', 'Limit Break', 'Juggernaut', 'Runic Pyramid', 'Sundial', 'Twin Daggers', 'Cloak Clasp', 'Gremlin Horn']
                    if relic.name in useful_relics or gold >= relic.price + 50:  # Keep some gold reserve
                        return BuyRelicAction(relic)
            
            # Priority 4: Buy potions if needed and affordable
            if not self.game.are_potions_full():
                for potion in screen.potions:
                    if gold >= potion.price:
                        # Prioritize useful potions
                        useful_potions = ['Healing Potion', 'Strength Potion', 'Fire Potion', 'Ice Potion', 'Block Potion', 'Strawberry']
                        if potion.name in useful_potions:
                            return BuyPotionAction(potion)
            
            # Priority 5: Purge as last resort if we have extra gold
            if screen.purge_available and gold >= purge_cost:
                return ChooseAction(name="purge")
            
            # No good purchases available
            return CancelAction()
        elif self.game.screen_type == ScreenType.GRID:
            if not self.game.choice_available:
                return ProceedAction()
            if self.game.screen.for_upgrade or self.choose_good_card:
                available_cards = self.priorities.get_sorted_cards(self.game.screen.cards)
            else:
                available_cards = self.priorities.get_sorted_cards(self.game.screen.cards, reverse=True)
            num_cards = self.game.screen.num_cards
            return CardSelectAction(available_cards[:num_cards])
        elif self.game.screen_type == ScreenType.HAND_SELECT:
            if not self.game.choice_available:
                return ProceedAction()
            # Usually, we don't want to choose the whole hand for a hand select. 3 seems like a good compromise.
            num_cards = min(self.game.screen.num_cards, 3)
            return CardSelectAction(self.priorities.get_cards_for_action(self.game.current_action, self.game.screen.cards, num_cards))
        else:
            return ProceedAction()

    def choose_rest_option(self):
        rest_options = self.game.screen.rest_options
        if len(rest_options) > 0 and not self.game.screen.has_rested:
            if RestOption.REST in rest_options and self.game.current_hp < self.game.max_hp / 2:
                return RestAction(RestOption.REST)
            elif RestOption.REST in rest_options and self.game.act != 1 and self.game.floor % 17 == 15 and self.game.current_hp < self.game.max_hp * 0.9:
                return RestAction(RestOption.REST)
            elif RestOption.SMITH in rest_options:
                return RestAction(RestOption.SMITH)
            elif RestOption.LIFT in rest_options:
                return RestAction(RestOption.LIFT)
            elif RestOption.DIG in rest_options:
                return RestAction(RestOption.DIG)
            elif RestOption.REST in rest_options and self.game.current_hp < self.game.max_hp:
                return RestAction(RestOption.REST)
            else:
                return ChooseAction(0)
        else:
            return ProceedAction()

    def count_copies_in_deck(self, card):
        count = 0
        for deck_card in self.game.deck:
            if deck_card.card_id == card.card_id:
                count += 1
        return count

    def choose_card_reward(self):
        reward_cards = self.game.screen.cards
        import sys
        can_skip = self.game.screen.can_skip if hasattr(self.game.screen, 'can_skip') else False
        in_combat = self.game.in_combat if hasattr(self.game, 'in_combat') else False
        sys.stderr.write(f"[CARD_REWARD] Floor {self.game.floor if hasattr(self.game, 'floor') else '?'}: {len(reward_cards)} cards, can_skip={can_skip}, in_combat={in_combat}\n")

        for i, card in enumerate(reward_cards):
            count = self.count_copies_in_deck(card)
            needs = self.priorities.needs_more_copies(card, count) if can_skip and not in_combat else True
            sys.stderr.write(f"  [{i}] {card.card_id} (copies={count}, needs_more={needs})\n")

        if can_skip and not in_combat:
            pickable_cards = [card for card in reward_cards if self.priorities.needs_more_copies(card, self.count_copies_in_deck(card))]
        else:
            pickable_cards = reward_cards

        if len(pickable_cards) > 0:
            potential_pick = self.priorities.get_best_card(pickable_cards)
            sys.stderr.write(f"[CARD_REWARD] Choosing: {potential_pick.card_id if potential_pick else 'None'}\n")
            return CardRewardAction(potential_pick)
        elif hasattr(self.game.screen, 'can_bowl') and self.game.screen.can_bowl:
            sys.stderr.write(f"[CARD_REWARD] Using bowl\n")
            return CardRewardAction(bowl=True)
        else:
            sys.stderr.write(f"[CARD_REWARD] Skipping all cards\n")
            self.skipped_cards = True
            return CancelAction()

    def generate_map_route(self):
        node_rewards = self.priorities.MAP_NODE_PRIORITIES.get(self.game.act)
        best_rewards = {0: {node.x: node_rewards[node.symbol] for node in self.game.map.nodes[0].values()}}
        best_parents = {0: {node.x: 0 for node in self.game.map.nodes[0].values()}}
        min_reward = min(node_rewards.values())
        map_height = max(self.game.map.nodes.keys())
        for y in range(0, map_height):
            best_rewards[y+1] = {node.x: min_reward * 20 for node in self.game.map.nodes[y+1].values()}
            best_parents[y+1] = {node.x: -1 for node in self.game.map.nodes[y+1].values()}
            for x in best_rewards[y]:
                node = self.game.map.get_node(x, y)
                best_node_reward = best_rewards[y][x]
                for child in node.children:
                    test_child_reward = best_node_reward + node_rewards[child.symbol]
                    if test_child_reward > best_rewards[y+1][child.x]:
                        best_rewards[y+1][child.x] = test_child_reward
                        best_parents[y+1][child.x] = node.x
        best_path = [0] * (map_height + 1)
        best_path[map_height] = max(best_rewards[map_height].keys(), key=lambda x: best_rewards[map_height][x])
        for y in range(map_height, 0, -1):
            best_path[y - 1] = best_parents[y][best_path[y]]
        self.map_route = best_path

    def make_map_choice(self):
        if len(self.game.screen.next_nodes) > 0 and self.game.screen.next_nodes[0].y == 0:
            self.generate_map_route()
            self.game.screen.current_node.y = -1
        if self.game.screen.boss_available:
            return ChooseMapBossAction()
        chosen_x = self.map_route[self.game.screen.current_node.y + 1]
        for choice in self.game.screen.next_nodes:
            if choice.x == chosen_x:
                return ChooseMapNodeAction(choice)
        # This should never happen
        return ChooseAction(0)


class OptimizedAgent(SimpleAgent):
    """
    Enhanced agent with modular decision system.

    This agent inherits from SimpleAgent for backward compatibility but uses
    advanced heuristics for decision making. It features:
    - Synergy-based card evaluation
    - Beam search combat planning
    - Adaptive strategy based on deck archetype
    - Context-aware decision making

    Usage:
        agent = OptimizedAgent(chosen_class=PlayerClass.THE_SILENT)
    """

    def __init__(self, chosen_class=PlayerClass.THE_SILENT,
                 use_optimized_combat=True,
                 use_optimized_card_selection=True):
        """
        Initialize OptimizedAgent.

        Args:
            chosen_class: Player class to use
            use_optimized_combat: Use enhanced combat planning (default: True)
            use_optimized_card_selection: Use synergy-based card evaluation (default: True)
        """
        # Initialize parent class
        super().__init__(chosen_class)

        # Check if optimized components are available
        if not OPTIMIZED_AI_AVAILABLE:
            # Silent fallback - no print statements
            use_optimized_combat = False
            use_optimized_card_selection = False

        # Configuration flags
        self.use_optimized_combat = use_optimized_combat
        self.use_optimized_card_selection = use_optimized_card_selection

        # Initialize game tracker
        if GameTracker is not None:
            self.game_tracker = GameTracker()
            self.game_tracker.player_class = str(chosen_class).replace('PlayerClass.', '')
        else:
            self.game_tracker = None
        self._in_combat = False
        self._last_relics = set()
        self._last_turn = 0

        # Initialize decision components if available
        if OPTIMIZED_AI_AVAILABLE:
            player_class_str = str(chosen_class).replace('PlayerClass.', '')

            # Use class-specific components for Ironclad
            if player_class_str == 'IRONCLAD':
                from spirecomm.ai.heuristics.ironclad_evaluator import IroncladCardEvaluator
                from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
                from spirecomm.ai.heuristics.ironclad_archetype import IroncladArchetypeManager
                from spirecomm.ai.heuristics.ironclad_deck import IroncladDeckStrategy
                from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter

                self.card_evaluator = IroncladCardEvaluator(player_class=player_class_str)
                self.combat_planner = IroncladCombatPlanner(card_evaluator=self.card_evaluator)
                self.archetype_manager = IroncladArchetypeManager()
                self.deck_strategy = IroncladDeckStrategy()
                self.map_router = AdaptiveMapRouter(player_class=player_class_str)
                self.deck_analyzer = DeckAnalyzer()  # Keep for compatibility
            else:
                # Use generic components for other classes
                self.card_evaluator = SynergyCardEvaluator(player_class=player_class_str)
                self.combat_planner = HeuristicCombatPlanner(
                    card_evaluator=self.card_evaluator,
                    player_class=player_class_str
                )
                self.deck_analyzer = DeckAnalyzer()
                self.archetype_manager = None
                self.deck_strategy = None
                # All classes get map router
                from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter
                self.map_router = AdaptiveMapRouter(player_class=player_class_str)

            # Track decision history for analysis
            self.decision_history = []

            # === 新增：存储规划的动作序列 ===
            self.current_action_sequence = []
            self.current_action_index = 0
        else:
            self.card_evaluator = None
            self.combat_planner = None
            self.deck_analyzer = None
            self.archetype_manager = None
            self.deck_strategy = None
            self.map_router = None
            self.decision_history = []
            self.current_action_sequence = []
            self.current_action_index = 0

    def get_play_card_action(self):
        """
        Override with optimized combat logic if enabled.

        Returns:
            PlayCardAction or EndTurnAction
        """
        try:
            if self.use_optimized_combat and self.combat_planner and OPTIMIZED_AI_AVAILABLE:
                return self._get_optimized_play_card_action()
            else:
                # Fall back to SimpleAgent logic
                return super().get_play_card_action()
        except Exception as e:
            # On error, print and fall back to simple logic
            import sys
            print(f"Error in optimized combat: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return super().get_play_card_action()

    def _get_optimized_play_card_action(self):
        """
        Use optimized combat planning with proper sequence execution.

        关键改变：存储并执行完整序列，不只是第一张卡

        Returns:
            PlayCardAction or EndTurnAction
        """
        if not self.game.play_available:
            return EndTurnAction()

        try:
            # 如果有待执行的序列，继续执行
            if self.current_action_sequence and self.current_action_index < len(self.current_action_sequence):
                action = self.current_action_sequence[self.current_action_index]
                self.current_action_index += 1

                # 验证动作仍然可执行
                if isinstance(action, PlayCardAction):
                    card_uuid = getattr(action.card, 'uuid', None) if action.card else None
                    hand_uuids = [getattr(c, 'uuid', None) for c in self.game.hand if hasattr(c, 'uuid')]
                    if card_uuid and card_uuid in hand_uuids:
                        return action
                    else:
                        # 卡不在手上了（不应该发生），重置序列
                        self.current_action_sequence = []
                        self.current_action_index = 0

            # 规划新序列
            context = DecisionContext(self.game)
            action_sequence = self.combat_planner.plan_turn(context)

            if action_sequence:
                # 存储序列用于执行
                self.current_action_sequence = action_sequence
                self.current_action_index = 0

                # 计算置信度
                confidence = 0.5  # 默认值
                if self.combat_planner and hasattr(self.combat_planner, 'get_confidence'):
                    try:
                        confidence = self.combat_planner.get_confidence(context)
                    except:
                        pass

                # 记录决策用于分析
                self.decision_history.append({
                    'type': 'combat',
                    'sequence': action_sequence,
                    'turn': context.turn,
                    'floor': context.floor,
                    'confidence': confidence
                })

                # 记录到 game_tracker
                if self.game_tracker:
                    self.game_tracker.record_decision(
                        decision_type='combat',
                        confidence=confidence,
                        used_fallback=False
                    )

                # 返回第一个动作
                return action_sequence[0]

            # 没有规划的动作 - 结束回合
            self.current_action_sequence = []
            return EndTurnAction()

        except Exception as e:
            import sys
            print(f"Error in _get_optimized_play_card_action: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            self.current_action_sequence = []
            return super().get_play_card_action()

    def get_next_action_in_game(self, game_state):
        """
        Override to detect turn changes, combat events, and track statistics.

        Args:
            game_state: Current game state
        """
        # 检测回合变化
        if hasattr(game_state, 'turn') and hasattr(self.game, 'turn'):
            if game_state.turn != self.game.turn:
                # 新回合 - 重置动作序列
                self.current_action_sequence = []
                self.current_action_index = 0

        # Track game statistics if available
        if self.game_tracker and hasattr(game_state, 'in_combat'):
            try:
                # 检测战斗状态变化
                current_in_combat = game_state.in_combat

                if current_in_combat and not self._in_combat:
                    # 战斗开始
                    room_type = "monster"
                    if hasattr(game_state, 'room_type'):
                        rt = str(game_state.room_type)
                        if "Elite" in rt:
                            room_type = "elite"
                        elif "Boss" in rt:
                            room_type = "boss"

                    self.game_tracker.start_combat(
                        floor=game_state.floor if hasattr(game_state, 'floor') else 0,
                        act=game_state.act if hasattr(game_state, 'act') else 1,
                        room_type=room_type
                    )
                    self._in_combat = True
                elif not current_in_combat and self._in_combat:
                    # 战斗结束
                    self.game_tracker.end_combat(
                        hp_remaining=game_state.current_hp if hasattr(game_state, 'current_hp') else 80,
                        max_hp=game_state.max_hp if hasattr(game_state, 'max_hp') else 80
                    )
                    self._in_combat = False

                # 检测遗物获得
                if hasattr(game_state, 'relics'):
                    current_relics = set(r.relic_id if hasattr(r, 'relic_id') else str(r) for r in game_state.relics)
                    new_relics = current_relics - self._last_relics
                    for relic_id in new_relics:
                        self.game_tracker.record_relic(relic_id)
                    self._last_relics = current_relics
            except Exception as e:
                # Silently fail on tracking errors to not break the game
                import sys
                print(f"Error in game tracking: {e}", file=sys.stderr)

        # 更新游戏状态
        self.game = game_state

        # 调用父类方法
        return super().get_next_action_in_game(game_state)

    def choose_card_reward(self):
        """
        Override with optimized card selection if enabled.

        Returns:
            CardRewardAction or CancelAction
        """
        if self.use_optimized_card_selection and self.card_evaluator and OPTIMIZED_AI_AVAILABLE:
            return self._choose_card_reward_optimized()
        else:
            return super().choose_card_reward()

    def _choose_card_reward_optimized(self):
        """
        Use synergy-based card selection.

        Returns:
            CardRewardAction or CancelAction
        """
        try:
            reward_cards = self.game.screen.cards

            if not reward_cards:
                return CancelAction()

            # Create decision context with error handling
            try:
                context = DecisionContext(self.game)
            except Exception as e:
                # If context creation fails, fall back to simple logic
                import sys
                print(f"Error creating DecisionContext: {e}", file=sys.stderr)
                return super().choose_card_reward()

            # Filter cards we would actually take
            if self.game.screen.can_skip and not self.game.in_combat:
                pickable_cards = [
                    card for card in reward_cards
                    if self.priorities.needs_more_copies(card, self.count_copies_in_deck(card))
                ]
            else:
                pickable_cards = reward_cards

            if not pickable_cards:
                if self.game.screen.can_bowl:
                    return CardRewardAction(bowl=True)
                else:
                    self.skipped_cards = True
                    # Track skipped card choice
                    if self.game_tracker:
                        self.game_tracker.record_card_choice(
                            chosen=None,
                            skipped=len(reward_cards),
                            available=[c.card_id for c in reward_cards]
                        )
                        # 记录跳过决策
                        self.game_tracker.record_decision(
                            decision_type='reward',
                            confidence=0.5,  # 跳过卡牌的置信度较低
                            used_fallback=False
                        )
                    return CancelAction()

            # Limit Break conditional check (A20 expert strategy)
            # Only pick Limit Break when we have Strength support
            limit_break_card = next((c for c in pickable_cards if c.card_id == 'Limit Break'), None)
            if limit_break_card:
                current_strength = context.strength if hasattr(context, 'strength') else 0

                # Check if we have Strength scaling cards
                strength_scaling_cards = ['Demon Form', 'Inflame', 'Spot Weakness']
                has_strength_scaling = any(
                    any(c.card_id == sc for sc in strength_scaling_cards)
                    for c in self.game.deck
                ) if hasattr(self.game, 'deck') and self.game.deck else False

                # Skip Limit Break if no Strength support
                if current_strength < 5 and not has_strength_scaling:
                    import sys
                    sys.stderr.write(f"[REWARD] Skipping Limit Break - no Strength support (Str={current_strength}, has_scaling={has_strength_scaling})\n")
                    pickable_cards = [c for c in pickable_cards if c.card_id != 'Limit Break']

                    if not pickable_cards:
                        # No other cards worth taking
                        if self.game.screen.can_bowl:
                            return CardRewardAction(bowl=True)
                        else:
                            return CancelAction()

            # Deck size limit check (keep deck lean)
            deck_size = len(self.game.deck) if hasattr(self.game, 'deck') and self.game.deck else 10
            if deck_size >= 18:
                import sys
                # Be very selective - only high priority cards
                # Get scores for all pickable cards
                scored_cards = []
                for card in pickable_cards:
                    try:
                        if self.card_evaluator:
                            card_score = self.card_evaluator.evaluate_card(card, context)
                            scored_cards.append((card, card_score))
                        else:
                            # Use simple fallback: only take if score looks good
                            # Default mid-tier score
                            card_score = 50
                            scored_cards.append((card, card_score))
                    except:
                        scored_cards.append((card, 50))  # Default score

                # Filter for high priority cards (score >= 65, reduced from 75 to reduce skipping)
                high_priority_cards = [
                    (card, card_score) for card, card_score in scored_cards
                    if card_score >= 65
                ]

                if high_priority_cards:
                    sys.stderr.write(f"[REWARD] Deck size {deck_size}, being selective (score >= 65)\n")
                    pickable_cards = [card for card, _ in high_priority_cards]
                else:
                    # No good cards - skip to keep deck lean
                    sys.stderr.write(f"[REWARD] Deck too large ({deck_size}) and no good cards (score >= 65) - skipping\n")
                    if self.game.screen.can_bowl:
                        return CardRewardAction(bowl=True)
                    else:
                        self.skipped_cards = True
                        if self.game_tracker:
                            self.game_tracker.record_card_choice(
                                chosen=None,
                                skipped=len(reward_cards),
                                available=[c.card_id for c in reward_cards]
                            )
                        return CancelAction()

            # Use synergy evaluator to rank cards
            try:
                best_card = self.card_evaluator.get_best_card(pickable_cards, context)
            except Exception as e:
                import sys
                print(f"Error in card evaluator: {e}", file=sys.stderr)
                # Fall back to simple logic
                return super().choose_card_reward()

            if best_card:
                # Track card choice
                if self.game_tracker:
                    self.game_tracker.record_card_choice(
                        chosen=best_card.card_id,
                        skipped=len(reward_cards) - 1,
                        available=[c.card_id for c in reward_cards]
                    )

                # Record decision
                self.decision_history.append({
                    'type': 'card_reward',
                    'card': best_card.card_id,
                    'floor': context.floor,
                    'archetype': context.deck_archetype
                })

                # Record to game_tracker
                if self.game_tracker:
                    self.game_tracker.record_decision(
                        decision_type='reward',
                        confidence=0.8,  # 卡牌选择默认置信度
                        used_fallback=False
                    )

                return CardRewardAction(best_card)
            else:
                return CancelAction()
        except Exception as e:
            import sys
            print(f"Error in _choose_card_reward_optimized: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Fall back to parent's logic
            return super().choose_card_reward()

    def use_next_potion(self):
        """
        Enhanced potion usage logic.

        Uses potions not just in boss fights but also in:
        - Elite fights when dangerous
        - High-damage situations
        - When potion provides high value
        - Based on potion type and current needs

        Returns:
            PotionAction or None
        """
        potions = self.game.get_real_potions()

        if not potions:
            return None

        # Calculate current needs
        hp_pct = self.game.current_hp / max(self.game.max_hp, 1)
        incoming_damage = self.get_incoming_damage()
        alive_monsters = [m for m in self.game.monsters if not m.is_gone and not m.half_dead]
        is_elite = 'Elite' in self.game.room_type
        is_boss = 'Boss' in self.game.room_type
        
        # Evaluate combat danger
        danger_level = self._evaluate_combat_danger(None)
        
        # Filter and prioritize potions based on situation
        potions_to_use = []
        
        for potion in potions:
            if not potion.can_use:
                continue
                
            # Prioritize potions based on situation
            use_potion = False
            
            # Healing potions - use when HP is low and in danger
            if 'heal' in potion.name.lower() or 'health' in potion.name.lower() or 'strawberry' in potion.name.lower() or 'apple' in potion.name.lower():
                # Use healing potions when HP is critical or in dangerous situations
                if (hp_pct < 0.3 or (hp_pct < 0.5 and danger_level > 0.5)) and incoming_damage > 0:
                    use_potion = True
                    potions_to_use.append((3, potion))
            
            # Damage potions - use when multiple monsters or dangerous enemies
            elif 'damage' in potion.name.lower() or 'strength' in potion.name.lower() or 'fire' in potion.name.lower() or 'ice' in potion.name.lower() or 'lightning' in potion.name.lower():
                # Use damage potions in elite/boss fights or when multiple monsters
                if (is_elite or is_boss or len(alive_monsters) >= 2) and danger_level > 0.4:
                    use_potion = True
                    potions_to_use.append((2, potion))
            
            # Defensive potions - use when incoming damage is high
            elif 'block' in potion.name.lower() or 'shield' in potion.name.lower() or 'barrier' in potion.name.lower():
                # Use defensive potions when incoming damage exceeds current HP or block
                current_block = sum(monster.block for monster in alive_monsters if hasattr(monster, 'block'))
                if incoming_damage > current_block + self.game.current_hp * 0.5:
                    use_potion = True
                    potions_to_use.append((1, potion))
            
            # Other potions - use based on general danger
            else:
                if danger_level > 0.7:
                    use_potion = True
                    potions_to_use.append((0, potion))
        
        # Sort potions by priority (highest first)
        potions_to_use.sort(reverse=True, key=lambda x: x[0])
        
        # Use the highest priority potion
        if potions_to_use:
            _, potion = potions_to_use[0]
            if potion.requires_target:
                # For damage potions, target highest HP monster; for others, target as appropriate
                if 'damage' in potion.name.lower():
                    target = max(alive_monsters, key=lambda m: m.current_hp)
                else:
                    target = self.get_low_hp_target()
                potion_action = PotionAction(True, potion=potion, target_monster=target)
            else:
                potion_action = PotionAction(True, potion=potion)
            
            if self.game_tracker:
                self.game_tracker.record_potion_use()
            
            return potion_action
        
        # Fallback: always use potions in boss fights if nothing else
        if is_boss:
            potion_action = super().use_next_potion()
            if potion_action and self.game_tracker:
                self.game_tracker.record_potion_use()
            return potion_action

        return None

    def _evaluate_combat_danger(self, context):
        """
        Evaluate how dangerous the current combat is (0-1).

        Considers:
        - Number of monsters
        - Incoming damage
        - Player HP percentage

        Args:
            context: DecisionContext (or None)

        Returns:
            Danger level 0-1
        """
        danger = 0.0

        # Monster count
        alive_monsters = [m for m in self.game.monsters if not m.is_gone and not m.half_dead]
        danger += min(len(alive_monsters) * 0.15, 0.4)

        # Incoming damage
        incoming = self.get_incoming_damage()
        if self.game.max_hp > 0:
            danger += min(incoming / self.game.max_hp, 0.4)

        # HP percentage
        hp_pct = self.game.current_hp / max(self.game.max_hp, 1)
        if hp_pct < 0.3:
            danger += 0.3

        # Elite or boss
        if 'Elite' in self.game.room_type or 'Boss' in self.game.room_type:
            danger += 0.2

        return min(danger, 1.0)

    def get_deck_stats(self):
        """
        Get statistics about current deck.

        Returns:
            Dictionary with deck metrics (if optimized components available)
        """
        if self.deck_analyzer and OPTIMIZED_AI_AVAILABLE:
            try:
                context = DecisionContext(self.game)
                return self.deck_analyzer.get_deck_stats(context)
            except Exception as e:
                return {'error': str(e)}
        else:
            return {'error': 'Deck analyzer not available'}

    def get_decision_summary(self):
        """
        Get summary of decisions made this game.

        Returns:
            Dictionary with decision statistics
        """
        if not self.decision_history:
            return {'total_decisions': 0}

        summary = {
            'total_decisions': len(self.decision_history),
            'combat_decisions': sum(1 for d in self.decision_history if d.get('type') == 'combat'),
            'card_rewards': sum(1 for d in self.decision_history if d.get('type') == 'card_reward'),
            'avg_confidence': 0
        }

        # Calculate average confidence for combat decisions
        combat_confidences = [d.get('confidence', 0) for d in self.decision_history if d.get('type') == 'combat']
        if combat_confidences:
            summary['avg_confidence'] = sum(combat_confidences) / len(combat_confidences)

        return summary

