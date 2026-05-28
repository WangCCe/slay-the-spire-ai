from types import SimpleNamespace

from spirecomm.ai.intent_utils import (
    intent_is_attack,
    intent_is_unknown,
    monster_intends_attack,
)
from spirecomm.spire.character import Intent


class _CustomIntent:
    def __init__(self, attacking):
        self.attacking = attacking

    def is_attack(self):
        return self.attacking


def test_intent_is_attack_accepts_enum_string_and_protocol_objects():
    assert intent_is_attack(Intent.ATTACK)
    assert intent_is_attack("Intent.ATTACK_DEBUFF")
    assert intent_is_attack(_CustomIntent(True))


def test_intent_is_attack_rejects_none_and_non_attack_intents():
    assert not intent_is_attack(None)
    assert not intent_is_attack(Intent.DEBUFF)
    assert not intent_is_attack("Intent.BUFF")
    assert not intent_is_attack(_CustomIntent(False))


def test_intent_is_unknown_accepts_intent_none_and_unknown_representations():
    assert intent_is_unknown(Intent.NONE)
    assert intent_is_unknown(Intent.UNKNOWN)
    assert intent_is_unknown("Intent.NONE")
    assert intent_is_unknown("UNKNOWN")


def test_intent_is_unknown_rejects_missing_and_concrete_intents():
    assert not intent_is_unknown(None)
    assert not intent_is_unknown(Intent.ATTACK)
    assert not intent_is_unknown("Intent.DEBUFF")


def test_monster_intends_attack_can_treat_missing_intent_as_known_or_unknown():
    missing = SimpleNamespace()
    explicit_none = SimpleNamespace(intent=None)
    attacker = SimpleNamespace(intent="Intent.ATTACK")

    assert monster_intends_attack(missing)
    assert monster_intends_attack(explicit_none)
    assert monster_intends_attack(attacker)

    assert not monster_intends_attack(missing, missing_intent_counts=False)
    assert not monster_intends_attack(explicit_none, missing_intent_counts=False)
