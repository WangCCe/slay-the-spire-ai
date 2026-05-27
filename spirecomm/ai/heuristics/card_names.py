"""Shared card-name normalization helpers for heuristic lookups."""

import re
from typing import Any


_UPGRADE_SUFFIX_RE = re.compile(r'\+\d*$')
_BASIC_CARD_SUFFIXES = ('_R', '_G', '_B', '_P')


def canonical_card_name(card: Any) -> str:
    raw_name = getattr(card, 'name', None) or getattr(card, 'card_id', None) or card
    card_name = _UPGRADE_SUFFIX_RE.sub('', str(raw_name))
    for suffix in _BASIC_CARD_SUFFIXES:
        if card_name.endswith(suffix):
            return card_name[:-len(suffix)]
    return card_name


def card_data_key(card: Any) -> str:
    return canonical_card_name(card).lower()
