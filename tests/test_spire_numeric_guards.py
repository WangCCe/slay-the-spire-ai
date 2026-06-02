from spirecomm.spire.numeric import coerce_float, coerce_int


def test_coerce_int_accepts_decimal_string_values():
    assert coerce_int("12.0") == 12
    assert coerce_int("-1.0") == -1


def test_coerce_int_uses_default_for_missing_or_invalid_values():
    assert coerce_int(None, default=7) == 7
    assert coerce_int("not-a-number", default=7) == 7


def test_coerce_int_uses_default_for_nonfinite_float_values():
    assert coerce_int(float("inf"), default=7) == 7
    assert coerce_int(float("-inf"), default=7) == 7
    assert coerce_int(float("nan"), default=7) == 7


def test_coerce_float_uses_default_for_missing_invalid_or_nonfinite_values():
    assert coerce_float(None, default=7.0) == 7.0
    assert coerce_float("not-a-number", default=7.0) == 7.0
    assert coerce_float("nan", default=7.0) == 7.0
    assert coerce_float("inf", default=7.0) == 7.0
