from types import SimpleNamespace

import numpy as np

from spirecomm.ai.rl.state_encoder import StateEncoder
from spirecomm.spire.character import Intent


def test_state_encoder_rejects_nonfinite_numeric_inputs():
    game = SimpleNamespace(
        player=SimpleNamespace(
            current_hp="nan",
            max_hp="80",
            energy="inf",
            block="-inf",
            powers=[],
            orbs=[
                SimpleNamespace(
                    orb_id="Lightning",
                    evoke_amount="nan",
                    passive_amount="inf",
                )
            ],
        ),
        character="IRONCLAD",
        gold="inf",
        floor="nan",
        act="1",
        ascension_level="nan",
        hand=[],
        deck=[],
        discard_pile=[],
        draw_pile=[],
        exhaust_pile=[],
        limbo=[],
        monsters=[
            SimpleNamespace(
                monster_id="Cultist",
                name="Cultist",
                current_hp="nan",
                max_hp="inf",
                block="nan",
                intent=Intent.ATTACK,
                move_adjusted_damage="inf",
                move_hits="nan",
                powers=[],
                move_id="nan",
                last_move_id="inf",
                second_last_move_id="-inf",
                is_gone=False,
                is_minion=False,
                half_dead=False,
            )
        ],
        relics=[],
        potions=[],
        room_type="MONSTER",
        in_combat=True,
        screen_type=None,
        choice_list=[],
        choice_available=False,
        screen=None,
        proceed_available=False,
        cancel_available=False,
        available_commands=[],
        cards_discarded_this_turn="nan",
        card_in_play=None,
        potion_available=False,
        room_phase=None,
        screen_up=False,
        play_available=True,
        end_available=True,
        act_boss=None,
    )

    state = StateEncoder().encode(game)

    assert state.shape == (781,)
    assert np.isfinite(state).all()
