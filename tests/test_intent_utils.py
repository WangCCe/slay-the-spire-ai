from types import SimpleNamespace

from spirecomm.ai.intent_utils import (
    intent_tokens,
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


def test_intent_tokens_normalizes_enum_dotted_and_slash_separated_intents():
    assert intent_tokens(Intent.ATTACK_DEBUFF) == {"ATTACK", "DEBUFF"}
    assert intent_tokens("Intent.DEFEND_BUFF") == {"DEFEND", "BUFF"}
    assert intent_tokens("Attack/Debuff") == {"ATTACK", "DEBUFF"}


def test_intent_tokens_does_not_conflate_buff_and_debuff():
    assert "BUFF" not in intent_tokens(Intent.DEBUFF)
    assert "DEBUFF" not in intent_tokens(Intent.BUFF)


def test_intent_is_attack_accepts_enum_string_and_protocol_objects():
    assert intent_is_attack(Intent.ATTACK)
    assert intent_is_attack("Intent.ATTACK_DEBUFF")
    assert intent_is_attack("Attack/Debuff")
    assert intent_is_attack(_CustomIntent(True))


def test_intent_is_attack_rejects_none_and_non_attack_intents():
    assert not intent_is_attack(None)
    assert not intent_is_attack(Intent.DEBUFF)
    assert not intent_is_attack("Intent.BUFF")
    assert not intent_is_attack("NOT_ATTACK")
    assert not intent_is_attack("NON_ATTACKING")
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
