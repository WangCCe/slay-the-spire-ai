from spirecomm.spire.numeric import coerce_int


def test_coerce_int_accepts_decimal_string_values():
    assert coerce_int("12.0") == 12
    assert coerce_int("-1.0") == -1


def test_coerce_int_uses_default_for_missing_or_invalid_values():
    assert coerce_int(None, default=7) == 7
    assert coerce_int("not-a-number", default=7) == 7
