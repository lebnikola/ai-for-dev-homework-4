import pytest

from money import AmountParseError, to_kopecks


@pytest.mark.parametrize(
    ("raw", "kopecks"),
    [
        ("5000", 500_000),
        ("5000,00", 500_000),
        ("5000.00", 500_000),
        ("5 000", 500_000),
        ("5\u00a0000", 500_000),
        ("12.34", 1_234),
        ("12,34", 1_234),
        ("5.000", 500_000),
        ("1,000", 100_000),
        ("1.234,56", 123_456),
        ("1,234.56", 123_456),
        ("1 234,56", 123_456),
        ("0,99", 99),
        ("5.5", 550),
        ("1 234,5", 123_450),
        ("0.01", 1),
    ],
)
def test_to_kopecks_valid(raw, kopecks):
    assert to_kopecks(raw) == kopecks


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "abc",
        "-500",
        "0",
        "0,00",
        "1.23.456",
        "12.3456",
        "5..5",
        "1,2,3",
        "5 000руб",
        "1 000 000 000 000",
    ],
)
def test_to_kopecks_invalid(raw):
    with pytest.raises(AmountParseError):
        to_kopecks(raw)
