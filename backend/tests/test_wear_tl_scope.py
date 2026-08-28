import pytest

from app.core.calculation.wear_tl_scope import (
    TensionLengthScope,
    classify_tension_length_scope,
)


@pytest.mark.parametrize(
    ("line_group", "identity"),
    [
        ("TML", "M01"),
        ("TML", "M1"),
        ("TML", "M33"),
        ("TML", "D01"),
        ("TML", "D60"),
        ("TML", "U01"),
        ("TML", "U55"),
        ("TML", "U07/1"),
        ("TML", "U7/2"),
        ("TML", "U08/2"),
        ("TML", "U31/1"),
        ("TML", "U36/2"),
        ("TML", "K01"),
        ("TML", "K16"),
        ("TML", "01"),
        ("TML", "1"),
        ("TML", "74"),
        ("EAL", "H01"),
        ("EAL", "H1"),
        ("EAL", "H52"),
        ("EAL", "H23D"),
        ("EAL", "H26D"),
        ("EAL", "D01"),
        ("EAL", "D31"),
        ("EAL", "U01"),
        ("EAL", "U55"),
        ("EAL", "U7/1"),
        ("EAL", "U08/2"),
        ("EAL", "U31/2"),
        ("EAL", "U36/1"),
        ("EAL", "K01"),
        ("EAL", "K16"),
        ("EAL", "1"),
        ("EAL", "01"),
        ("EAL", "76"),
        ("EAL", "69B"),
        ("EAL", "70A"),
        ("EAL", "L01"),
        ("EAL", "L20"),
        ("EAL", "T2"),
        ("EAL", "T3"),
        ("EAL", "X36"),
        ("EAL", "X37"),
        ("EAL", "X50"),
        ("EAL", "X53"),
        ("EAL", "X54"),
    ],
)
def test_classifies_approved_mainline_identities(line_group, identity):
    assert (
        classify_tension_length_scope(line_group, identity)
        is TensionLengthScope.MAINLINE
    )


@pytest.mark.parametrize(
    ("line_group", "identity"),
    [
        ("TML", "MX1"),
        ("TML", "MX09"),
        ("TML", "MX11"),
        ("TML", "MD1"),
        ("TML", "MD22"),
        ("TML", "MP24"),
        ("TML", "EM1"),
        ("TML", "PT1"),
        ("TML", "PT2"),
        ("TML", "CT1"),
        ("TML", "CT3"),
        ("TML", "KX1"),
        ("TML", "KX07"),
        ("TML", "X01"),
        ("TML", "X29"),
        ("TML", "W1-1"),
        ("TML", "27A"),
        ("TML", "101"),
        ("TML", "102"),
        ("TML", "103"),
        ("TML", "Neutral Section"),
        ("EAL", "HX02"),
        ("EAL", "X01"),
        ("EAL", "X35"),
        ("EAL", "X38"),
        ("EAL", "X39"),
        ("EAL", "LX1"),
        ("EAL", "LX009"),
        ("EAL", "D32"),
        ("EAL", "D33"),
        ("EAL", "EM1"),
        ("EAL", "Neutral Section"),
    ],
)
def test_classifies_approved_siding_identities(line_group, identity):
    assert (
        classify_tension_length_scope(line_group, identity)
        is TensionLengthScope.SIDING
    )


@pytest.mark.parametrize(
    ("line_group", "identity"),
    [
        ("TML", "M00"),
        ("TML", "M34"),
        ("TML", "D61"),
        ("TML", "U56"),
        ("TML", "U09/1"),
        ("TML", "K17"),
        ("TML", "0"),
        ("TML", "75"),
        ("TML", "MX12"),
        ("TML", "MD23"),
        ("TML", "MP23"),
        ("TML", "X30"),
        ("TML", "HX02"),
        ("EAL", "H00"),
        ("EAL", "H53"),
        ("EAL", "H24D"),
        ("EAL", "D34"),
        ("EAL", "U56"),
        ("EAL", "U09/1"),
        ("EAL", "K17"),
        ("EAL", "0"),
        ("EAL", "77"),
        ("EAL", "L21"),
        ("EAL", "T1"),
        ("EAL", "T4"),
        ("EAL", "X40"),
        ("EAL", "X51"),
        ("EAL", "MX1"),
        ("EAL", "27A"),
        ("EAL", ""),
        ("TML", "new infrastructure"),
    ],
)
def test_unknown_identities_fail_closed(line_group, identity):
    assert (
        classify_tension_length_scope(line_group, identity)
        is TensionLengthScope.UNKNOWN
    )


def test_classification_is_case_insensitive_and_trims_whitespace():
    assert (
        classify_tension_length_scope(" eal ", " x36 ")
        is TensionLengthScope.MAINLINE
    )
    assert (
        classify_tension_length_scope("tml", " neutral section ")
        is TensionLengthScope.SIDING
    )


def test_colliding_families_are_fully_anchored():
    assert classify_tension_length_scope("TML", "D22") is TensionLengthScope.MAINLINE
    assert classify_tension_length_scope("TML", "MD22") is TensionLengthScope.SIDING
    assert classify_tension_length_scope("TML", "X07") is TensionLengthScope.SIDING
    assert classify_tension_length_scope("TML", "MX07") is TensionLengthScope.SIDING
    assert classify_tension_length_scope("TML", "KX07") is TensionLengthScope.SIDING
    assert classify_tension_length_scope("EAL", "X36") is TensionLengthScope.MAINLINE
    assert classify_tension_length_scope("EAL", "HX02") is TensionLengthScope.SIDING


@pytest.mark.parametrize("line_group", [None, "", "WRL", 123])
def test_rejects_unsupported_line_groups(line_group):
    with pytest.raises(ValueError, match="EAL or TML"):
        classify_tension_length_scope(line_group, "1")
