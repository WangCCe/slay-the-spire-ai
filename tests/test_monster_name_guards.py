from types import SimpleNamespace

from spirecomm.ai import monster_names
import spirecomm.ai.incoming_damage as incoming_damage
from spirecomm.ai.heuristics.enhanced_monster_database import EnhancedMonsterDatabase
import spirecomm.ai.heuristics.simulation as simulation


def test_live_monster_name_normalization_uses_one_shared_helper():
    monster = SimpleNamespace(name="Slaver", monster_id="SlaverRed")

    assert monster_names.canonical_live_monster_name(monster) == "Red Slaver"
    assert incoming_damage.canonical_live_monster_name is monster_names.canonical_live_monster_name
    assert simulation._canonical_live_monster_name is monster_names.canonical_live_monster_name


def test_live_monster_name_normalization_covers_ids_when_display_name_missing():
    assert monster_names.canonical_live_monster_name(
        SimpleNamespace(name="", monster_id="FungiBeast")
    ) == "Fungi Beast"
    assert monster_names.canonical_live_monster_name(
        SimpleNamespace(name="", monster_id="TheGuardian")
    ) == "The Guardian"
    assert monster_names.canonical_live_monster_name(
        SimpleNamespace(name="", monster_id="AwakenedOne")
    ) == "Awakened One"


def test_live_bronze_orb_id_reaches_enhanced_monster_data():
    database = EnhancedMonsterDatabase()
    live_monster = SimpleNamespace(name="Orb", monster_id="BronzeOrb")

    canonical_name = monster_names.canonical_live_monster_name(live_monster)
    move_names = {move["name"] for move in database.get_moves(canonical_name)}

    assert canonical_name == "Bronze Orb"
    assert {"Stasis", "Beam"} <= move_names
