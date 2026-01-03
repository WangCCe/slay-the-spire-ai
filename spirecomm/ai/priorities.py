import math

class Priority:

    CARD_PRIORITY_LIST = []

    PLAY_PRIORITY_LIST = []

    AOE_CARDS = []

    DEFENSIVE_CARDS = []

    MAX_COPIES = {}

    GROUP_MAX_COPIES = {}  # 分组限制：一组卡牌共享数量限制

    BOSS_RELIC_PRIORITY_LIST = []

    MAP_NODE_PRIORITIES_1 = {'R': 1000, 'E': 10, '$': 100, '?': 100, 'M': 1, 'T': 0}

    MAP_NODE_PRIORITIES_2 = {'R': 1000, 'E': 100, '$': 10, '?': 10, 'M': 1, 'T': 0}

    MAP_NODE_PRIORITIES_3 = {'R': 1000, 'E': 1, '$': 100, '?': 100, 'M': 10, 'T': 0}

    GOOD_CARD_ACTIONS = [
        "PutOnDeckAction",
        "ArmamentsAction",
        "DualWieldAction",
        "NightmareAction",
        "RetainCardsAction",
        "SetupAction"
    ]

    BAD_CARD_ACTIONS = [
        "DiscardAction",
        "ExhaustAction",
        "PutOnBottomOfDeckAction",
        "RecycleAction",
        "ForethoughtAction",
        "GamblingChipAction"
    ]

    def __init__(self):
        self.CARD_PRIORITIES = {self.CARD_PRIORITY_LIST[i]: i for i in range(len(self.CARD_PRIORITY_LIST))}
        self.PLAY_PRIORITIES = {self.PLAY_PRIORITY_LIST[i]: i for i in range(len(self.PLAY_PRIORITY_LIST))}
        self.BOSS_RELIC_PRIORITIES = {self.BOSS_RELIC_PRIORITY_LIST[i]: i for i in range(len(self.BOSS_RELIC_PRIORITY_LIST))}
        self.MAP_NODE_PRIORITIES = {
            1: self.MAP_NODE_PRIORITIES_1,
            2: self.MAP_NODE_PRIORITIES_2,
            3: self.MAP_NODE_PRIORITIES_3,
            4: self.MAP_NODE_PRIORITIES_3  # Doesn't really matter anyway
        }

    def get_best_card(self, card_list):
        return min(card_list, key=lambda x: self.CARD_PRIORITIES.get(x.card_id, math.inf) - 0.5 * x.upgrades)

    def get_worst_card(self, card_list):
        return max(card_list, key=lambda x: self.CARD_PRIORITIES.get(x.card_id, math.inf) - 0.5 * x.upgrades)

    def get_sorted_cards(self, card_list, reverse=False):
        return sorted(card_list, key=lambda x: self.CARD_PRIORITIES.get(x.card_id, math.inf) - 0.5 * x.upgrades, reverse=reverse)

    def get_sorted_cards_to_play(self, card_list, reverse=False):
        return sorted(card_list, key=lambda x: self.PLAY_PRIORITIES.get(x.card_id, math.inf) - 0.5 * x.upgrades, reverse=reverse)

    def get_best_card_to_play(self, card_list):
        return min(card_list, key=lambda x: self.PLAY_PRIORITIES.get(x.card_id, math.inf) - 0.5 * x.upgrades)

    def get_worst_card_to_play(self, card_list):
        return max(card_list, key=lambda x: self.PLAY_PRIORITIES.get(x.card_id, math.inf) - 0.5 * x.upgrades)

    def should_skip(self, card):
        card_priority = self.CARD_PRIORITIES.get(card.card_id, math.inf)
        skip_priority = self.CARD_PRIORITIES.get("Skip", float('inf'))
        return card_priority > skip_priority

    def needs_more_copies(self, card, num_copies, deck=None):
        """
        Check if we need more copies of a card.

        Args:
            card: The card to check
            num_copies: Current copies of this specific card
            deck: Full deck (optional, for group limit calculation)

        Returns:
            True if we should take this card
        """
        # Check if card belongs to a group with shared limit
        if deck is not None and card.card_id in self.MAX_COPIES:
            limit = self.MAX_COPIES[card.card_id]
            # If limit is a string, it's a group reference
            if isinstance(limit, str):
                return self._check_group_limit(card, limit, deck)

        # Original logic for individual limits
        return self.MAX_COPIES.get(card.card_id, 0) > num_copies

    def _check_group_limit(self, card, group_name, deck):
        """
        Check if taking this card would exceed the group limit.

        Args:
            card: The card we want to take
            group_name: Name of the group (string)
            deck: Current deck

        Returns:
            True if within group limit, False otherwise
        """
        # Get all cards in this group
        group_cards = [
            card_id for card_id, limit in self.MAX_COPIES.items()
            if isinstance(limit, str) and limit == group_name
        ]

        # Count how many cards from this group are already in deck
        group_count = sum(
            1 for deck_card in deck
            if deck_card.card_id in group_cards
        )

        # Get the group limit
        group_limit = self.GROUP_MAX_COPIES.get(group_name, 0)

        return group_count < group_limit

    def get_best_boss_relic(self, relic_list):
        return min(relic_list, key=lambda x: self.BOSS_RELIC_PRIORITIES.get(x.relic_id, 0))

    def is_card_aoe(self, card):
        return card.card_id in self.AOE_CARDS

    def is_card_defensive(self, card):
        return card.card_id in self.DEFENSIVE_CARDS

    def get_cards_for_action(self, action, cards, max_cards):
        if action in self.GOOD_CARD_ACTIONS:
            sorted_cards = self.get_sorted_cards(cards, reverse=False)
        else:
            sorted_cards = self.get_sorted_cards(cards, reverse=True)
        num_cards = min(max_cards, len(cards))
        return sorted_cards[:num_cards]


class SilentPriority(Priority):

    CARD_PRIORITY_LIST = [
        "Footwork",
        "After Image",
        "Noxious Fumes",
        "Crippling Poison",
        "Apotheosis",
        "A Thousand Cuts",
        "Adrenaline",
        "Malaise",
        "Caltrops",
        "Corpse Explosion",
        "Dagger Spray",
        "PiercingWail",
        "Neutralize",
        "Survivor",
        "Well Laid Plans",
        "Backflip",
        "Dodge and Roll",
        "Infinite Blades",
        "Leg Sweep",
        "Backstab",
        "Glass Knife",
        "Dash",
        "J.A.X.",
        "Master of Strategy",
        "Escape Plan",
        "Cloak And Dagger",
        "Die Die Die",
        "Blur",
        "Deadly Poison",
        "Predator",
        "Deflect",
        "Flying Knee",
        "Skip",
        "Shiv",
        "Trip",
        "Good Instincts",
        "Burst",
        "Dark Shackles",
        "Terror",
        "Discovery",
        "Bane",
        "Deep Breath",
        "Violence",
        "Panache",
        "All Out Attack",
        "Catalyst",
        "Sucker Punch",
        "Secret Technique",
        "Bouncing Flask",
        "Poisoned Stab",
        "Envenom",
        "Impatience",
        "The Bomb",
        "Blind",
        "Mayhem",
        "HandOfGreed",
        "RitualDagger",
        "Bandage Up",
        "Bite",
        "Quick Slash",
        "Calculated Gamble",
        "Acrobatics",
        "Endless Agony",
        "Dagger Throw",
        "Bullet Time",
        "Flash of Steel",
        "Outmaneuver",
        "Tools of the Trade",
        "Chrysalis",
        "Finesse",
        "Ghostly",
        "Defend_G",
        "Expertise",
        "Panacea",
        "Doppelganger",
        "Skewer",
        "Slice",
        "Blade Dance",
        "Swift Strike",
        "Thinking Ahead",
        "Dramatic Entrance",
        "Madness",
        "Strike_G",
        "Phantasmal Killer",
        "Heel Hook",
        "Magnetism",
        "Finisher",
        "Flechettes",
        "Prepared",
        "Secret Weapon",
        "Distraction",
        "Metamorphosis",
        "PanicButton",
        "Night Terror",
        "Enlightenment",
        "Sadistic Nature",
        "Unload",
        "Choke",
        "Masterful Stab",
        "Transmutation",
        "Accuracy",
        "Purity",
        "Concentrate",
        "Underhanded Strike",
        "Jack Of All Trades",
        "Wraith Form v2",
        "Storm of Steel",
        "Eviscerate",
        "Riddle With Holes",
        "Setup",
        "Venomology",
        "Mind Blast",
        "Tactician",
        "Forethought",
        "Reflex",
        "Grand Finale",
        "Dazed",
        "Void",
        "AscendersBane",
        "Necronomicurse",
        "Slimed",
        "Wound",
        "Burn",
        "Clumsy",
        "Parasite",
        "Injury",
        "Shame",
        "Decay",
        "Writhe",
        "Doubt",
        "Regret",
        "Pain",
        "Normality",
        "Pride",
    ]

    DEFENSIVE_CARDS = [
        "Cloak and Dagger",
        "Leg Sweep",
        "Deflect",
        "Blur",
        "Escape Plan",
        "Survivor",
        "Defend_G",
        "Backflip",
        "PiercingWail",
        "Dodge and Roll",
        "Dark Shackles",
        "PanicButton",
        "Finesse",
        "Good Instincts"
    ]

    PLAY_PRIORITY_LIST = [
        "Apotheosis",
        "After Image",
        "Footwork",
        "Well Laid Plans",
        "A Thousand Cuts",
        "Noxious Fumes",
        "Caltrops",
        "Infinite Blades",
        "Crippling Poison",
        "Adrenaline",
        "Neutralize",
        "Glass Knife",
        "Madness",
        "Dash",
        "Backflip",
        "Blur",
        "Malaise",
        "Dagger Spray",
        "Corpse Explosion",
        "Leg Sweep",
        "Deadly Poison",
        "Dodge and Roll",
        "Survivor",
        "PiercingWail",
        "Backstab",
        "J.A.X.",
        "Master of Strategy",
        "Escape Plan",
        "Cloak And Dagger",
        "Die Die Die",
        "Predator",
        "Flying Knee",
        "Shiv",
        "Trip",
        "Good Instincts",
        "Burst",
        "Dark Shackles",
        "Terror",
        "Discovery",
        "Bane",
        "Deep Breath",
        "Violence",
        "Panache",
        "All Out Attack",
        "Deflect",
        "Sucker Punch",
        "Secret Technique",
        "Bouncing Flask",
        "Poisoned Stab",
        "Envenom",
        "Impatience",
        "The Bomb",
        "Blind",
        "Mayhem",
        "HandOfGreed",
        "RitualDagger",
        "Bandage Up",
        "Bite",
        "Quick Slash",
        "Calculated Gamble",
        "Acrobatics",
        "Endless Agony",
        "Catalyst",
        "Dagger Throw",
        "Bullet Time",
        "Flash of Steel",
        "Outmaneuver",
        "Tools of the Trade",
        "Chrysalis",
        "Finesse",
        "Ghostly",
        "Defend_G",
        "Expertise",
        "Panacea",
        "Doppelganger",
        "Skewer",
        "Slice",
        "Blade Dance",
        "Swift Strike",
        "Thinking Ahead",
        "Dramatic Entrance",
        "Strike_G",
        "Phantasmal Killer",
        "Heel Hook",
        "Magnetism",
        "Finisher",
        "Flechettes",
        "Prepared",
        "Secret Weapon",
        "Distraction",
        "Metamorphosis",
        "PanicButton",
        "Night Terror",
        "Enlightenment",
        "Sadistic Nature",
        "Unload",
        "Choke",
        "Masterful Stab",
        "Transmutation",
        "Accuracy",
        "Purity",
        "Concentrate",
        "Underhanded Strike",
        "Jack Of All Trades",
        "Wraith Form v2",
        "Storm of Steel",
        "Eviscerate",
        "Riddle With Holes",
        "Setup",
        "Venomology",
        "Mind Blast",
        "Tactician",
        "Forethought",
        "Reflex",
        "Grand Finale",
        "Dazed",
        "Void",
        "AscendersBane",
        "Necronomicurse",
        "Slimed",
        "Wound",
        "Burn",
        "Clumsy",
        "Parasite",
        "Injury",
        "Shame",
        "Decay",
        "Writhe",
        "Doubt",
        "Regret",
        "Pain",
        "Normality",
        "Pride",

    ]

    AOE_CARDS = [
        "Dagger Spray",
        "Die Die Die",
        "Crippling Poison",
        "All Out Attack"
    ]

    MAX_COPIES = {
        "Corpse Explosion": 1,
        "Footwork": 3,
        "After Image": 99,
        "Noxious Fumes": 2,
        "Crippling Poison": 1,
        "Apotheosis": 1,
        "Adrenaline": 99,
        "Malaise": 1,
        "Caltrops": 2,
        "Dagger Spray": 1,
        "PiercingWail": 2,
        "Neutralize": 1,
        "Survivor": 1,
        "Well Laid Plans": 1,
        "Backflip": 3,
        "Dodge and Roll": 1,
        "A Thousand Cuts": 1,
        "Infinite Blades": 1,
        "Leg Sweep": 2,
        "Dash": 1,
        "Flying Knee": 1,
        "J.A.X.": 1,
        "Master of Strategy": 99,
        "Escape Plan": 99,
        "Cloak And Dagger": 2,
        "Die Die Die": 2,
        "Blur": 3,
        "Deadly Poison": 1,
        "Predator": 1,
        "Deflect": 1,
        "Backstab": 2,
        "Glass Knife": 1,
    }

    BOSS_RELIC_PRIORITY_LIST = [
        "Sozu",
        "Philosopher's Stone",
        "Runic Dome",
        "Cursed Key",
        "Fusion Hammer",
        "Ectoplasm",
        "Velvet Choker",
        "Busted Crown",
        "Empty Cage",
        "Astrolabe",
        "Runic Pyramid",
        "Snecko Eye",
        "Pandora's Box",
        "Ring of the Serpent",
        "Lizard Tail",
        "Eternal Feather",
        "Coffee Dripper",
        "Tiny House",
        "Black Star",
        "Orrery",
        "Runic Cube",
        "WristBlade",
        "HoveringKite",
        "White Beast Statue",
        "Calling Bell",
    ]


class IroncladPriority(Priority):

    CARD_PRIORITY_LIST = [
        # === 90-100 分 (神级) - From Tier List ===
        "Offering",

        # === 80-90 分 (顶级) ===
        "Burning Pact",
        "Second Wind",
        "Battle Trance",

        # === 70-80 分 (优秀) ===
        "Shockwave",
        "Dark Embrace",

        # === 60-70 分 (良好) ===
        "Impervious",
        "Fiend Fire",
        "Immolate",
        "Blood for Blood",
        "Feel No Pain",

        # === 50-60 分 (中等) ===
        "Pommel Strike",
        "Spot Weakness",
        "Evolve",
        "Shrug It Off",
        "Armaments",
        "Havoc",
        "Hemokinesis",

        # === 40-50 分 (中等偏下) ===
        "Feed",
        "Anger",
        "Inflame",
        "Rage",
        "Bloodletting",

        # === 30-40 分 (较差) ===
        "Body Slam",
        "Corruption",
        "Headbutt",
        "Reckless Charge",
        "Reaper",

        # === 20-30 分 (差) ===
        "Carnage",
        "Uppercut",
        "Ghostly Armor",
        "Rampage",
        "Brutality",
        "Sever Soul",

        # === SKIP MARKER (Tier List: 跳过 26.8% 在 20-30 分) ===
        "Skip",

        # === 10-20 分 (很差) ===
        "Flame Barrier",
        "True Grit",
        "Combust",
        "Barricade",
        "Power Through",
        "Fire Breathing",
        "Infernal Blade",
        "Exhume",
        "Searing Blow",

        # === 5-10 分 (极差) ===
        "Juggernaut",
        "Pummel",
        "Whirlwind",
        "Berserk",

        # === 1-5 分 (几乎不可用) ===
        "Bludgeon",
        "Double Tap",
        "Twin Strike",
        "Demon Form",
        "Dual Wield",
        "Perfected Strike",
        "Dropkick",
        "Clash",

        # === 0-1 分 (垃圾) ===
        "Strike_R",
        "Defend_R",
        "Bash",
        "Intimidate",
        "Iron Wave",
        "Flex",
        "Rupture",
        "Cleave",
        "Thunderclap",
        "Warcry",
        "Sentinel",
        "Wild Strike",
        "Limit Break",
        "Entrench",
        "Seeing Red",

        # === 其他卡牌 (不在 Tier List 中，添加到最后) ===
        "Apotheosis",
        "Ghostly",
        "Metallicize",
        "Disarm",
        "Master of Strategy",
        "Secret Weapon",
        "Finesse",
        "Mayhem",
        "Panache",
        "Secret Technique",
        "Metamorphosis",
        "Thinking Ahead",
        "Madness",
        "Discovery",
        "Chrysalis",
        "Deep Breath",
        "Trip",
        "Enlightenment",
        "Heavy Blade",
        "Clothesline",
        "Bandage Up",
        "Panacea",
        "Shiv",
        "RitualDagger",
        "Swift Strike",
        "Magnetism",
        "Mind Blast",
        "AscendersBane",
        "Dazed",
        "Void",
        "Blind",
        "Good Instincts",
        "Dark Shackles",
        "Sword Boomerang",
        "Dramatic Entrance",
        "HandOfGreed",
        "Violence",
        "Bite",
        "Purity",
        "Sadistic Nature",
        "Transmutation",
        "Slimed",
        "Impatience",
        "The Bomb",
        "Jack Of All Trades",
        "Forethought",
        "Clumsy",
        "Parasite",
        "Shame",
        "Injury",
        "Wound",
        "Writhe",
        "Doubt",
        "Burn",
        "Decay",
        "Regret",
        "Necronomicurse",
        "Pain",
        "Normality",
        "Pride",
        "Flame of Life",
    ]

    DEFENSIVE_CARDS = [
        "Power Through",
        "True Grit",
        "Impervious",
        "Shrug It Off",
        "Flame Barrier",
        "Entrench",
        "Defend_R",
        "Sentinel",
        "Second Wind",
        "Ghostly Armor",
        "Dark Shackles",
        "PanicButton",
        "Rage"
    ]

    PLAY_PRIORITY_LIST = [
        "Apotheosis",
        "Offering",
        "Demon Form",
        "Inflame",
        "Metallicize",
        "Disarm",
        "Shockwave",
        "Ghostly",
        "Limit Break",
        "Double Tap",
        "Thunderclap",
        "Immolate",
        "Uppercut",
        "Flame Barrier",
        "Shrug It Off",
        "Impervious",
        "Madness",
        "Perfected Strike",
        "Battle Trance",
        "Rage",
        "Master of Strategy",
        "Pommel Strike",
        "J.A.X.",
        "Flash of Steel",
        "Flex",
        "Anger",
        "Defend_R",
        "Bash",
        "Whirlwind",
        "PanicButton",
        "Secret Weapon",
        "Finesse",
        "Mayhem",
        "Panache",
        "Secret Technique",
        "Metamorphosis",
        "Thinking Ahead",
        "Discovery",
        "Chrysalis",
        "Deep Breath",
        "Trip",
        "Enlightenment",
        "Heavy Blade",
        "Feed",
        "Fiend Fire",
        "Twin Strike",
        "Headbutt",
        "Seeing Red",
        "Combust",
        "Clash",
        "Dark Shackles",
        "Sword Boomerang",
        "Dramatic Entrance",
        "Bludgeon",
        "HandOfGreed",
        "Evolve",
        "Violence",
        "Bite",
        "Carnage",
        "Clothesline",
        "Bandage Up",
        "Panacea",
        "Reckless Charge",
        "Infernal Blade",
        "Spot Weakness",
        "Strike_R",
        "Shiv",
        "Havoc",
        "RitualDagger",
        "Dropkick",
        "Feel No Pain",
        "Swift Strike",
        "Corruption",
        "Magnetism",
        "Bloodletting",
        "Iron Wave",
        "Armaments",
        "Mind Blast",
        "AscendersBane",
        "Dazed",
        "Void",
        "Rampage",
        "Ghostly Armor",
        "True Grit",
        "Blind",
        "Good Instincts",
        "Pummel",
        "Hemokinesis",
        "Exhume",
        "Reaper",
        "Cleave",
        "Warcry",
        "Purity",
        "Dual Wield",
        "Wild Strike",
        "Body Slam",
        "Sever Soul",
        "Burning Pact",
        "Brutality",
        "Barricade",
        "Intimidate",
        "Juggernaut",
        "Sadistic Nature",
        "Dark Embrace",
        "Power Through",
        "Transmutation",
        "Sentinel",
        "Rupture",
        "Slimed",
        "Fire Breathing",
        "Second Wind",
        "Impatience",
        "The Bomb",
        "Jack Of All Trades",
        "Searing Blow",
        "Blood for Blood",
        "Berserk",
        "Entrench",
        "Forethought",
        "Clumsy",
        "Parasite",
        "Shame",
        "Injury",
        "Wound",
        "Writhe",
        "Doubt",
        "Burn",
        "Decay",
        "Regret",
        "Necronomicurse",
        "Pain",
        "Normality",
        "Pride"
    ]

    AOE_CARDS = [
        "Cleave",
        "Immolate",
        "Thunderclap",
        "Whirlwind"
    ]

    GROUP_MAX_COPIES = {
        "transition_attack": 2,  # 前期过渡攻击牌，总共限制2张
        "basic_defense": 1,      # 基础防御牌，总共限制1张
    }

    MAX_COPIES = {
        # === 分组限制：前期过渡卡牌 ===
        "Bash": "transition_attack",           # Vulnerable很重要，前期必带
        "Iron Wave": "transition_attack",      # 攻击+block，前期很实用
        "True Grit": "basic_defense",          # block+exhaust，前期防御
        "Clothesline": "transition_attack",    # 攻击+stun，控制很实用
        "Cleave": "transition_attack",         # 基础AOE
        "Thunderclap": "transition_attack",    # AOE+weak
        "Uppercut": "transition_attack",       # 攻击+weak
        "Pummel": "transition_attack",         # 多次攻击

        # === 基于 Tier List 的限制策略 ===

        # 90-100 分 (神级) - 鼓励获取
        "Offering": 2,  # 90-100分

        # 80-90 分 (顶级) - 鼓励获取
        "Burning Pact": 2,  # 80-90分
        "Second Wind": 1,  # 80-90分
        "Battle Trance": 2,  # 80-90分

        # 70-80 分 (优秀) - 可以获取
        "Shockwave": 1,  # 70-80分
        "Dark Embrace": 1,  # 70-80分

        # 60-70 分 (良好) - 适量获取
        "Impervious": 2,  # 60-70分
        "Fiend Fire": 1,  # 60-70分
        "Immolate": 1,  # 60-70分
        "Blood for Blood": 1,  # 60-70分
        "Feel No Pain": 2,  # 60-70分

        # 50-60 分 (中等) - 限制数量
        "Pommel Strike": 1,  # 50-60分
        "Spot Weakness": 1,  # 50-60分
        "Evolve": 1,  # 50-60分
        "Shrug It Off": 2,  # 50-60分
        "Armaments": 1,  # 50-60分
        "Havoc": 1,  # 50-60分
        "Hemokinesis": 1,  # 50-60分

        # 40-50 分 (中等偏下) - 严格限制
        "Feed": 1,  # 40-50分
        "Anger": 1,  # 40-50分
        "Inflame": 1,  # 40-50分
        "Rage": 2,  # 40-50分
        "Bloodletting": 1,  # 40-50分

        # 30-40 分 (较差) - 尽量不拿
        "Body Slam": 0,  # 30-40分，不鼓励
        "Corruption": 1,  # 30-40分
        "Headbutt": 1,  # 30-40分
        "Reckless Charge": 0,  # 30-40分，不鼓励
        "Reaper": 1,  # 30-40分

        # 20-30 分 (差) - 几乎不拿
        "Carnage": 0,  # 20-30分
        # "Uppercut": 分组限制 (transition_attack)
        "Ghostly Armor": 0,  # 20-30分
        "Rampage": 0,  # 20-30分
        "Brutality": 0,  # 20-30分
        "Sever Soul": 0,  # 20-30分

        # 10-20 分及以下 - 不拿
        "Flame Barrier": 0,  # 10-20分
        # "True Grit": 分组限制 (basic_defense)
        "Combust": 0,  # 10-20分
        "Barricade": 0,  # 10-20分
        "Power Through": 0,  # 10-20分
        "Fire Breathing": 0,  # 10-20分
        "Infernal Blade": 0,  # 10-20分
        "Exhume": 0,  # 10-20分
        "Searing Blow": 0,  # 10-20分
        "Juggernaut": 0,  # 5-10分
        # "Pummel": 分组限制 (transition_attack)
        "Whirlwind": 0,  # 5-10分
        "Berserk": 0,  # 5-10分

        # 1-5 分 (几乎不可用) - 绝不拿
        "Bludgeon": 0,  # 1-5分
        "Double Tap": 0,  # 1-5分
        "Twin Strike": 0,  # 1-5分
        "Demon Form": 0,  # 1-5分
        "Dual Wield": 0,  # 1-5分
        "Perfected Strike": 0,  # 1-5分
        "Dropkick": 0,  # 1-5分
        "Clash": 0,  # 1-5分

        # 0-1 分 (垃圾) - 绝不拿
        "Strike_R": 0,  # 0-1分，尽快移除
        "Defend_R": 0,  # 0-1分，尽快移除
        # "Bash": 分组限制 (transition_attack)
        "Intimidate": 0,  # 0-1分
        # "Iron Wave": 分组限制 (transition_attack)
        "Flex": 0,  # 0-1分
        "Rupture": 0,  # 0-1分
        # "Cleave": 分组限制 (transition_attack)
        # "Thunderclap": 分组限制 (transition_attack)
        "Warcry": 0,  # 0-1分
        "Sentinel": 0,  # 0-1分
        "Wild Strike": 0,  # 0-1分
        "Limit Break": 0,  # 0-1分
        "Entrench": 0,  # 0-1分
        "Seeing Red": 0,  # 0-1分

        # 其他卡牌 (不在 Tier List 中) - 保守限制
        "Apotheosis": 1,
        "Ghostly": 1,
        "Metallicize": 0,
        "Disarm": 1,
        "Master of Strategy": 1,
        "Secret Weapon": 0,
        "Finesse": 0,
        "Mayhem": 0,
        "Panache": 0,
        "Secret Technique": 0,
        "Metamorphosis": 0,
        "Thinking Ahead": 0,
        "Madness": 1,
        "Discovery": 1,
        "Chrysalis": 0,
        "Deep Breath": 0,
        "Trip": 0,
        "Enlightenment": 0,
        "Heavy Blade": 0,
        # "Clothesline": 分组限制 (transition_attack)
        "Bandage Up": 0,
        "Panacea": 0,
        "Shiv": 0,
        "RitualDagger": 0,
        "Swift Strike": 0,
        "Magnetism": 0,
        "Mind Blast": 0,
        "AscendersBane": 0,
        "Dazed": 0,
        "Void": 0,
        "Blind": 0,
        "Good Instincts": 0,
        "Dark Shackles": 0,
        "Sword Boomerang": 0,
        "Dramatic Entrance": 0,
        "HandOfGreed": 0,
        "Violence": 0,
        "Bite": 0,
        "Purity": 1,
        "Sadistic Nature": 0,
        "Transmutation": 0,
        "Slimed": 0,
        "Impatience": 0,
        "The Bomb": 0,
        "Jack Of All Trades": 0,
        "Forethought": 0,
        "Clumsy": 0,
        "Parasite": 0,
        "Shame": 0,
        "Injury": 0,
        "Wound": 0,
        "Writhe": 0,
        "Doubt": 0,
        "Burn": 0,
        "Decay": 0,
        "Regret": 0,
        "Necronomicurse": 0,
        "Pain": 0,
        "Normality": 0,
        "Pride": 0,
        "Flame of Life": 0,
        "PanicButton": 1,
    }

    BOSS_RELIC_PRIORITY_LIST = [
        "Sozu",
        "Snecko Eye",
        "Philosopher's Stone",
        "Runic Dome",
        "Cursed Key",
        "Fusion Hammer",
        "Velvet Choker",
        "Ectoplasm",
        "Mark of Pain",
        "Busted Crown",
        "Empty Cage",
        "Astrolabe",
        "Runic Pyramid",
        "Lizard Tail",
        "Eternal Feather",
        "Coffee Dripper",
        "Black Blood",
        "Tiny House",
        "Black Star",
        "Orrery",
        "Runic Cube",
        "Pandora's Box",
        "White Beast Statue",
        "Calling Bell",
    ]


class DefectPowerPriority(Priority):

    CARD_PRIORITY_LIST = [
        "Echo Form",
        "Electrodynamics",
        "Defragment",
        "Biased Cognition",
        "Glacier",
        "Self Repair",
        "Apotheosis",
        "Machine Learning",
        "Static Discharge",
        "Loop",
        "Buffer",
        "Capacitor",
        "Ball Lightning",
        "Cold Snap",
        "Undo",  # Equilibrium
        "Creative AI",
        "Conserve Battery",
        "Steam",  # Steam Barrier
        "Compile Driver",
        "Reinforced Body",
        "White Noise",
        "Force Field",
        "Chill",
        "Core Surge",
        "Rainbow",
        "Streamline",
        "Turbo",
        "Coolheaded",
        "Zap",
        "Dualcast",
        "BootSequence",
        "Leap",
        "Dark Shackles",
        "PanicButton",
        "RitualDagger",
        "Panache",
        "Master of Strategy",
        "Amplify",
        "Skip",
        "Storm",
        "Heatsinks",
        "Consume",
        "Seek",
        "Discovery",
        "Finesse",
        "Magnetism",
        "Blind",
        "Thunder Strike",
        "Sunder",
        "Reboot",
        "All For One",
        "Hologram",
        "Bite",
        "Deep Breath",
        "Tempest",
        "Sweeping Beam",
        "Trip",
        "Steam Power",  # Overclock
        "Dramatic Entrance",
        "Impatience",
        "The Bomb",
        "Bandage Up",
        "Secret Technique",
        "Violence",
        "Mayhem",
        "HandOfGreed",
        "Flash of Steel",
        "Genetic Algorithm",
        "Go for the Eyes",
        "Metamorphosis",
        "Doom and Gloom",
        "Ghostly",
        "Good Instincts",
        "Thinking Ahead",
        "Defend_B",
        "Madness",
        "J.A.X.",
        "Swift Strike",
        "Secret Weapon",
        "Multi-Cast",
        "Double Energy",
        "Auto Shields",
        "Chaos",
        "Jack Of All Trades",
        "FTL",
        "Lockon",
        "Melter",
        "Panacea",
        "Gash",  # Claw
        "Rip and Tear",
        "Barrage",
        "Hyperbeam",
        "Strike_B",
        "Mind Blast",
        "Sadistic Nature",
        "Meteor Strike",
        "Fusion",
        "Skim",
        "Fission",
        "Darkness",
        "Recycle",
        "Scrape",
        "Beam Cell",
        "Shiv",
        "Redo",  # Recursion
        "Hello World",
        "Stack",
        "Reprogram",
        "Enlightenment",
        "Transmutation",
        "Chrysalis",
        "Purity",
        "Rebound",
        "Aggregate",
        "Blizzard",
        "Forethought",
        "Void",
        "Dazed",
        "AscendersBane",
        "Clumsy",
        "Necronomicurse",
        "Slimed",
        "Wound",
        "Burn",
        "Parasite",
        "Injury",
        "Shame",
        "Doubt",
        "Writhe",
        "Decay",
        "Regret",
        "Pain",
        "Pride",
        "Normality",
    ]

    MAX_COPIES = {
        "Echo Form": 2,
        "Electrodynamics": 2,
        "Defragment": 10,
        "Glacier": 3,
        "Self Repair": 1,
        "Apotheosis": 1,
        "Machine Learning": 1,
        "Static Discharge": 2,
        "Loop": 3,
        "Buffer": 2,
        "Capacitor": 2,
        "Ball Lightning": 2,
        "Cold Snap": 2,
        "Undo": 2,  # Equilibrium
        "Amplify": 2,
        "Creative AI": 1,
        "Conserve Battery": 3,
        "Compile Driver": 2,
        "Reinforced Body": 1,
        "White Noise": 1,
        "Force Field": 1,
        "Chill": 1,
        "Core Surge": 1,
        "Rainbow": 1,
        "Streamline": 1,
        "Turbo": 1,
        "Coolheaded": 3,
        "Zap": 1,
        "Dualcast": 1,
        "BootSequence": 1,
        "Leap": 1,
        "Dark Shackles": 1,
        "PanicButton": 1,
        "RitualDagger": 1,
        "Panache": 1,
        "Master of Strategy": 5,
        "Steam": 2
    }

    AOE_CARDS = [
        "Electrodynamics"
    ]

    DEFENSIVE_CARDS = [
        "Genetic Algorithm",
        "Steam",
        "Glacier",
        "Stack",
        "BootSequence",
        "Coolheaded",
        "Force Field",
        "Reinforced Body",
        "Conserve Battery",
        "Defend_B",
        "Auto Shields",
        "Hologram",
        "Leap",
        "PanicButton",
        "Dark Shackles",
        "Finesse",
        "Good Instincts",
        "Turbo",
    ]

    BOSS_RELIC_PRIORITY_LIST = [
        "Sozu",
        "Snecko Eye",
        "Philosopher's Stone",
        "Nuclear Battery",
        "Runic Dome",
        "Cursed Key",
        "Fusion Hammer",
        "Velvet Choker",
        "Ectoplasm",
        "Busted Crown",
        "Inserter",
        "Empty Cage",
        "Astrolabe",
        "Runic Pyramid",
        "Lizard Tail",
        "Eternal Feather",
        "Coffee Dripper",
        "Tiny House",
        "Black Star",
        "Orrery",
        "Pandora's Box",
        "White Beast Statue",
        "Calling Bell",
        "FrozenCore",
    ]

    PLAY_PRIORITY_LIST = [
        "Apotheosis",
        "Double Energy",
        "Amplify",
        "Echo Form",
        "Electrodynamics",
        "Defragment",
        "Storm",
        "Glacier",
        "Self Repair",
        "Machine Learning",
        "Static Discharge",
        "Loop",
        "White Noise",
        "Madness",
        "Buffer",
        "Capacitor",
        "Core Surge",
        "Biased Cognition",
        "Ball Lightning",
        "Cold Snap",
        "Undo",  # Equilibrium
        "Creative AI",
        "Conserve Battery",
        "Steam",  # Steam Barrier
        "Steam Power",
        "Compile Driver",
        "Reinforced Body",
        "Seek",
        "Force Field",
        "Chill",
        "Rainbow",
        "Streamline",
        "Turbo",
        "Coolheaded",
        "Consume",
        "Zap",
        "Dualcast",
        "BootSequence",
        "Heatsinks",
        "Leap",
        "Dark Shackles",
        "PanicButton",
        "RitualDagger",
        "Panache",
        "Master of Strategy",
        "Skip",
        "Discovery",
        "Finesse",
        "Magnetism",
        "Blind",
        "Thunder Strike",
        "Sunder",
        "All For One",
        "Hologram",
        "Bite",
        "Deep Breath",
        "Tempest",
        "Sweeping Beam",
        "Trip",
        "Dramatic Entrance",
        "Impatience",
        "The Bomb",
        "Bandage Up",
        "Secret Technique",
        "Violence",
        "Mayhem",
        "HandOfGreed",
        "Flash of Steel",
        "Reboot",
        "Genetic Algorithm",
        "Go for the Eyes",
        "Metamorphosis",
        "Doom and Gloom",
        "Ghostly",
        "Good Instincts",
        "Thinking Ahead",
        "Defend_B",
        "J.A.X.",
        "Swift Strike",
        "Secret Weapon",
        "Multi-Cast",
        "Auto Shields",
        "Chaos",
        "Jack Of All Trades",
        "FTL",
        "Lockon",
        "Melter",
        "Panacea",
        "Gash",  # Claw
        "Rip and Tear",
        "Barrage",
        "Hyperbeam",
        "Strike_B",
        "Mind Blast",
        "Sadistic Nature",
        "Meteor Strike",
        "Fusion",
        "Skim",
        "Fission",
        "Darkness",
        "Recycle",
        "Scrape",
        "Beam Cell",
        "Shiv",
        "Redo",  # Recursion
        "Hello World",
        "Stack",
        "Reprogram",
        "Enlightenment",
        "Transmutation",
        "Chrysalis",
        "Purity",
        "Rebound",
        "Aggregate",
        "Blizzard",
        "Forethought",
        "Void",
        "Dazed",
        "AscendersBane",
        "Clumsy",
        "Necronomicurse",
        "Slimed",
        "Wound",
        "Burn",
        "Parasite",
        "Injury",
        "Shame",
        "Doubt",
        "Writhe",
        "Decay",
        "Regret",
        "Pain",
        "Pride",
        "Normality",
    ]

    # Don't fight early Act 1 elites - build power first (A20 expert consensus)
    # Priorities: Rest >> Shop ≈ Event > Monster >>> Elite (early game)
    # Only consider elites late Act 1 or when HP is high enough to survive.
    MAP_NODE_PRIORITIES_1 = {'R': 1000, 'E': -10, '$': 85, '?': 85, 'M': 60, 'T': 0}

    MAP_NODE_PRIORITIES_2 = {'R': 100, 'E': -1000, '$': 10, '?': 10, 'M': 1, 'T': 0}

    MAP_NODE_PRIORITIES_3 = {'R': 1000, 'E': 10, '$': 100, '?': 100, 'M': 1, 'T': 0}
