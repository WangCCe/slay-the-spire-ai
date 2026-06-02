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
