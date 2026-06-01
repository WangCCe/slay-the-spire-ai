from types import SimpleNamespace

import spirecomm.ai.decision.base as decision_base
from spirecomm.ai.decision.base import DecisionContext, EnemyThreatProfiler, ThreatCategory
from spirecomm.spire.card import Card, CardRarity, CardType
from spirecomm.spire.character import Intent


class _FakeCardDataLoader:
    def __init__(self, cards):
        self.cards = cards

    def get_card_data(self, card_name):
        return self.cards.get(card_name.lower())


class _FakeEnhancedMonsterDataLoader:
    def get_enhanced_monster_data(self, monster_name):
        return {"name": monster_name}

    def predict_monster_moves(self, monster_name, turn, monster_hp_percent):
        return []

    def get_monster_threat_profile(self, monster_name):
        return None

    def get_monster_special_mechanics(self, monster_name):
        return None


class _CanonicalOnlyMonsterDataLoader:
    def __init__(self):
        self.enhanced_names = []
        self.predicted_names = []
        self.profile_names = []
        self.special_names = []

    def get_enhanced_monster_data(self, monster_name):
        self.enhanced_names.append(monster_name)
        if monster_name == "Red Slaver":
            return {"name": "Red Slaver"}
        return None

    def predict_monster_moves(self, monster_name, turn, monster_hp_percent):
        self.predicted_names.append(monster_name)
        return [
            {
                "move": {"name": "Stab", "damage": 10},
                "confidence": 1.0,
            }
        ]

    def get_monster_threat_profile(self, monster_name):
        self.profile_names.append(monster_name)
        return {"scaling_threat": 10}

    def get_monster_special_mechanics(self, monster_name):
        self.special_names.append(monster_name)
        return None


def _context_for_deck(deck):
    context = DecisionContext.__new__(DecisionContext)
    context.game = SimpleNamespace(deck=deck)
    return context


def test_legacy_deck_archetype_uses_display_name_for_basic_card_ids(monkeypatch):
    monkeypatch.setattr(
        decision_base,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "strike": {
                    "description": "Deal 6 damage.",
                    "type": "ATTACK",
                    "cost": "1",
                },
            }
        ),
    )
    deck = [
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC, cost=1)
        for _ in range(4)
    ]

    assert _context_for_deck(deck)._analyze_deck_archetype() == "strength"


def test_legacy_deck_archetype_accepts_name_only_card_keyword(monkeypatch):
    monkeypatch.setattr(
        decision_base,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "quick draw": {
                    "description": "Useful setup.",
                    "type": "SKILL",
                    "cost": "1",
                },
            }
        ),
    )
    deck = [SimpleNamespace(name="Quick Draw")]

    assert _context_for_deck(deck)._analyze_deck_archetype() == "draw"


def test_legacy_synergies_use_display_name_for_basic_attack_ids(monkeypatch):
    monkeypatch.setattr(
        decision_base,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "uppercut": {
                    "description": "Deal 13 damage. Apply 1 Weak. Apply 1 Vulnerable.",
                    "type": "ATTACK",
                    "cost": "2",
                },
                "strike": {
                    "description": "Deal 6 damage.",
                    "type": "ATTACK",
                    "cost": "1",
                },
            }
        ),
    )
    deck = [
        Card("Uppercut", "Uppercut+", CardType.ATTACK, CardRarity.UNCOMMON, upgrades=1, cost=2),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC, cost=1),
    ]

    synergies = _context_for_deck(deck)._calculate_synergies()

    assert synergies["vulnerable"] > 0
    assert synergies["weak"] > 0


def test_legacy_synergies_accept_name_only_catalyst_cards(monkeypatch):
    monkeypatch.setattr(
        decision_base,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "catalyst": {
                    "description": "Double a status.",
                    "type": "SKILL",
                    "cost": "1",
                },
                "deadly poison": {
                    "description": "Apply 5 Poison.",
                    "type": "SKILL",
                    "cost": "1",
                },
            }
        ),
    )
    deck = [
        SimpleNamespace(name="Catalyst"),
        SimpleNamespace(name="Deadly Poison"),
    ]

    synergies = _context_for_deck(deck)._calculate_synergies()

    assert synergies["poison"] > 0


def test_incoming_damage_ignores_zero_hp_stale_monsters():
    monster = SimpleNamespace(
        is_gone=False,
        half_dead=False,
        current_hp=0,
        intent="Intent.ATTACK",
        move_adjusted_damage=12,
        move_hits=1,
    )
    context = DecisionContext.__new__(DecisionContext)
    context.game = SimpleNamespace(monsters=[monster])
    context.act = 1

    assert context._calculate_incoming_damage() == 0


def test_incoming_damage_clamps_negative_live_move_damage_to_zero():
    monster = SimpleNamespace(
        is_gone=False,
        half_dead=False,
        current_hp=20,
        intent="Intent.ATTACK",
        move_adjusted_damage=-3,
        move_hits=2,
    )
    context = DecisionContext.__new__(DecisionContext)
    context.game = SimpleNamespace(monsters=[monster])
    context.act = 1

    assert context._calculate_incoming_damage() == 0


def test_incoming_damage_estimates_unknown_intent_by_act():
    monster = SimpleNamespace(
        is_gone=False,
        half_dead=False,
        current_hp=20,
        intent=Intent.NONE,
        move_adjusted_damage=None,
        move_hits=1,
    )
    context = DecisionContext.__new__(DecisionContext)
    context.game = SimpleNamespace(monsters=[monster])
    context.act = 2

    assert context._calculate_incoming_damage() == 10


def test_incoming_damage_counts_known_unknown_damage_move():
    monster = SimpleNamespace(
        name="Exploder",
        monster_id="Exploder",
        is_gone=False,
        half_dead=False,
        current_hp=30,
        intent=Intent.UNKNOWN,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    context = DecisionContext.__new__(DecisionContext)
    context.game = SimpleNamespace(monsters=[monster])
    context.act = 3

    assert context._calculate_incoming_damage() == 30


def test_incoming_damage_ignores_known_no_damage_unknown_moves():
    monsters = [
        SimpleNamespace(
            name="Slime Boss",
            monster_id="Slime_Boss",
            is_gone=False,
            half_dead=False,
            current_hp=99,
            max_hp=140,
            intent=Intent.UNKNOWN,
            move_id=1,
            move_adjusted_damage=0,
            move_hits=1,
        ),
        SimpleNamespace(
            name="Acid Slime (L)",
            monster_id="Acid_Slime_L",
            is_gone=False,
            half_dead=False,
            current_hp=15,
            max_hp=65,
            intent=Intent.UNKNOWN,
            move_id=3,
            move_adjusted_damage=0,
            move_hits=1,
        ),
    ]
    context = DecisionContext.__new__(DecisionContext)
    context.game = SimpleNamespace(monsters=monsters)
    context.act = 2

    assert context._calculate_incoming_damage() == 0


def test_incoming_damage_ignores_missing_intent_without_damage():
    monster = SimpleNamespace(
        is_gone=False,
        half_dead=False,
        current_hp=20,
        intent=None,
        move_adjusted_damage=None,
        move_hits=1,
    )
    context = DecisionContext.__new__(DecisionContext)
    context.game = SimpleNamespace(monsters=[monster])
    context.act = 2

    assert context._calculate_incoming_damage() == 0


def test_decision_context_accepts_power_name_only_objects():
    monster = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        is_gone=False,
        half_dead=False,
        current_hp=48,
        max_hp=48,
        intent=Intent.DEBUFF,
        move_adjusted_damage=0,
        move_hits=1,
        powers=[
            SimpleNamespace(power_name="Vulnerable", amount=2),
            SimpleNamespace(power_name="Weak", amount=1),
        ],
    )
    game = SimpleNamespace(
        current_hp=70,
        max_hp=80,
        player=SimpleNamespace(
            energy=3,
            powers=[
                SimpleNamespace(power_name="Strength", amount=2),
                SimpleNamespace(power_name="Dexterity", amount=1),
            ],
        ),
        turn=1,
        floor=3,
        act=1,
        monsters=[monster],
        deck=[],
        hand=[],
        relics=[],
    )

    context = DecisionContext(game)

    assert context.strength == 2
    assert context.dexterity == 1
    assert context.vulnerable_stacks[0] == 2
    assert context.weak_stacks[0] == 1


def test_decision_context_accepts_relic_strings_and_names():
    game = SimpleNamespace(
        current_hp=70,
        max_hp=80,
        player=SimpleNamespace(energy=3, powers=[]),
        turn=1,
        floor=3,
        act=1,
        monsters=[],
        deck=[],
        hand=[],
        relics=[
            "Snecko Eye",
            SimpleNamespace(name="Orichalcum"),
            SimpleNamespace(relic_id="Paper Crane"),
        ],
    )

    context = DecisionContext(game)

    assert context.has_snecko_eye is True
    assert context.has_orichalcum is True
    assert context.has_paper_crane is True


def test_decision_context_treats_missing_is_playable_as_playable():
    strike = SimpleNamespace(name="Strike", cost=1, cost_for_turn=1)
    wound = SimpleNamespace(name="Wound", is_playable=False)
    game = SimpleNamespace(
        current_hp=70,
        max_hp=80,
        player=SimpleNamespace(energy=3, powers=[]),
        turn=1,
        floor=3,
        act=1,
        monsters=[],
        deck=[],
        hand=[strike, wound],
        relics=[],
    )

    context = DecisionContext(game)

    assert context.playable_cards == [strike]


def test_base_immediate_threat_clamps_negative_live_move_damage_to_zero():
    monster = SimpleNamespace(
        move_adjusted_damage=-3,
        move_hits=2,
        strength=0,
    )
    context = DecisionContext.__new__(DecisionContext)

    assert context._compute_base_immediate_threat(monster) == 0


def test_base_immediate_threat_ignores_non_attack_intents():
    monster = SimpleNamespace(
        intent=Intent.DEBUFF,
        move_adjusted_damage=12,
        move_hits=2,
        strength=0,
    )
    context = DecisionContext.__new__(DecisionContext)

    assert context._compute_base_immediate_threat(monster) == 0


def test_compute_threat_counts_actual_attack_debuff_intent_as_debuff_threat():
    monster = SimpleNamespace(
        name="Jaw Worm",
        intent=Intent.ATTACK_DEBUFF,
        move_adjusted_damage=7,
        move_hits=1,
        strength=0,
        current_hp=10,
        max_hp=100,
    )
    context = DecisionContext.__new__(DecisionContext)

    assert context.compute_threat(monster) == 17


def test_compute_threat_counts_actual_debuff_intent_as_debuff_threat():
    monster = SimpleNamespace(
        name="Acid Slime (L)",
        intent=Intent.DEBUFF,
        move_adjusted_damage=0,
        move_hits=1,
        strength=0,
        current_hp=10,
        max_hp=100,
    )
    context = DecisionContext.__new__(DecisionContext)

    assert context.compute_threat(monster) == 10


def test_compute_threat_uses_live_monster_id_for_legacy_scaling_names():
    monster = SimpleNamespace(
        name="Automaton",
        monster_id="BronzeAutomaton",
        intent=Intent.NONE,
        move_adjusted_damage=0,
        move_hits=1,
        strength=0,
        current_hp=30,
        max_hp=300,
    )
    context = DecisionContext.__new__(DecisionContext)

    assert context.compute_threat(monster) == 15


def test_compute_threat_v2_counts_actual_debuff_intent_as_debuff_threat(monkeypatch):
    monkeypatch.setattr(
        decision_base,
        "game_data_loader",
        _FakeEnhancedMonsterDataLoader(),
    )
    monster = SimpleNamespace(
        name="Acid Slime (L)",
        intent=Intent.DEBUFF,
        move_adjusted_damage=0,
        move_hits=1,
        strength=0,
        current_hp=10,
        max_hp=100,
    )
    context = DecisionContext.__new__(DecisionContext)
    context.turn = 1
    context.monsters_alive = [monster]

    assert context.compute_threat_v2(monster) == 10


def test_compute_threat_v2_does_not_count_debuff_intent_as_party_buff(monkeypatch):
    monkeypatch.setattr(
        decision_base,
        "game_data_loader",
        _FakeEnhancedMonsterDataLoader(),
    )
    monster = SimpleNamespace(
        name="Acid Slime (L)",
        intent=Intent.DEBUFF,
        move_adjusted_damage=0,
        move_hits=1,
        strength=0,
        current_hp=10,
        max_hp=100,
    )
    first_ally = SimpleNamespace(name="Spike Slime (M)")
    second_ally = SimpleNamespace(name="Spike Slime (S)")
    context = DecisionContext.__new__(DecisionContext)
    context.turn = 1
    context.monsters_alive = [monster, first_ally, second_ally]

    assert context.compute_threat_v2(monster) == 10


def test_compute_threat_v2_uses_live_monster_id_for_enhanced_data(monkeypatch):
    data_loader = _CanonicalOnlyMonsterDataLoader()
    monkeypatch.setattr(decision_base, "game_data_loader", data_loader)
    monster = SimpleNamespace(
        name="Slaver",
        monster_id="SlaverRed",
        intent=Intent.NONE,
        move_adjusted_damage=0,
        move_hits=1,
        strength=0,
        current_hp=30,
        max_hp=60,
    )
    context = DecisionContext.__new__(DecisionContext)
    context.turn = 1
    context.monsters_alive = [monster]

    assert context.compute_threat_v2(monster) > context.compute_threat(monster)
    assert data_loader.enhanced_names == ["Red Slaver"]
    assert data_loader.predicted_names == ["Red Slaver"]
    assert data_loader.profile_names == ["Red Slaver"]
    assert data_loader.special_names == ["Red Slaver"]


def test_enemy_threat_profiler_uses_live_monster_id_for_automaton():
    live_automaton = SimpleNamespace(
        name="Automaton",
        monster_id="BronzeAutomaton",
    )

    assert EnemyThreatProfiler().analyze_threat([live_automaton]) == ThreatCategory.ELITE


def test_enemy_threat_profiler_detects_power_name_scaling():
    cultist = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        powers=[SimpleNamespace(power_name="Ritual", amount=3)],
    )

    assert EnemyThreatProfiler().analyze_threat([cultist]) == ThreatCategory.SCALING


def test_enemy_threat_profiler_cache_tracks_power_changes():
    cultist = SimpleNamespace(
        name="Cultist",
        monster_id="Cultist",
        powers=[],
    )
    profiler = EnemyThreatProfiler()

    assert profiler.analyze_threat([cultist]) == ThreatCategory.REGULAR

    cultist.powers.append(SimpleNamespace(power_name="Ritual", amount=3))

    assert profiler.analyze_threat([cultist]) == ThreatCategory.SCALING
