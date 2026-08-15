from types import SimpleNamespace

import numpy as np

from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2
from spirecomm.spire.character import Intent


class _IdMapper:
    def card_id(self, _card_id):
        return 0

    def potion_id(self, _potion_id):
        return 0

    def relic_id(self, _relic_id):
        return 0

    def card_tag_list(self, _card_id):
        return []


def _monster(hp, max_hp=40, *, is_gone=False, half_dead=False):
    return SimpleNamespace(
        current_hp=hp,
        max_hp=max_hp,
        block=0,
        intent=Intent.BUFF,
        move_adjusted_damage=0,
        move_hits=0,
        powers=[],
        is_gone=is_gone,
        half_dead=half_dead,
    )


def test_state_encoder_rejects_nonfinite_numeric_inputs():
    game = SimpleNamespace(
        player=SimpleNamespace(
            current_hp="nan",
            max_hp="80",
            energy="inf",
            block="-inf",
            powers=[],
        ),
        monsters=[
            SimpleNamespace(
                current_hp="nan",
                max_hp="inf",
                block="nan",
                intent=Intent.ATTACK,
                move_adjusted_damage="inf",
                move_hits="nan",
                powers=[],
                is_gone=False,
            )
        ],
        floor="nan",
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        hand=[],
        character="IRONCLAD",
        screen_type=None,
        in_combat=True,
        potions=[],
        relics=[],
    )

    encoded = StateEncoderV2(id_mapper=_IdMapper()).encode(game)

    assert np.isfinite(encoded.continuous).all()


def test_state_encoder_coerces_power_amounts_before_keyword_encoding():
    encoder = StateEncoderV2(id_mapper=_IdMapper())

    strength = encoder._encode_keyword(
        [SimpleNamespace(power_id="Strength", amount="2.0")],
        "Strength",
    )
    poison = encoder._encode_keyword(
        [SimpleNamespace(power_id="Poison", amount="nan")],
        "Poison",
    )

    assert np.isclose(strength, np.tanh(0.2))
    assert poison == 0.0


def test_state_encoder_treats_half_dead_monsters_as_not_alive():
    game = SimpleNamespace(
        player=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            energy=3,
            block=0,
            powers=[],
        ),
        monsters=[
            SimpleNamespace(
                current_hp=12,
                max_hp=40,
                block=0,
                intent=Intent.BUFF,
                move_adjusted_damage=0,
                move_hits=0,
                powers=[],
                is_gone=False,
                half_dead=True,
            )
        ],
        floor=35,
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        hand=[],
        character="IRONCLAD",
        screen_type=None,
        in_combat=True,
        potions=[],
        relics=[],
    )

    encoded = StateEncoderV2(id_mapper=_IdMapper()).encode(game)

    first_monster_alive = encoded.continuous[StateEncoderV2.PLAYER_FEATURES]
    assert first_monster_alive == 0.0


def test_state_encoder_compacts_late_live_monster_into_first_slot():
    encoder = StateEncoderV2(id_mapper=_IdMapper())
    game = SimpleNamespace(monsters=[_monster(0) for _ in range(6)] + [_monster(12)])

    features = encoder._encode_monsters(game)

    assert features[0] == 1.0
    assert np.isclose(features[1], 0.3)
    assert features[StateEncoderV2.MONSTER_FEATURES :] == [
        0.0
    ] * (4 * StateEncoderV2.MONSTER_FEATURES)
