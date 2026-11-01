
from backend.app.analysis import calculate_growth


def test_growth_calculation():
    data = [
        {
            "fiscal_year": 2024,
            "revenue_usd": 245_122_000_000,
            "net_income_usd": 88_136_000_000,
            "revenue_usd_billions": 245.122,
            "net_income_usd_billions": 88.136,
        },
        {
            "fiscal_year": 2025,
            "revenue_usd": 281_724_000_000,
            "net_income_usd": 101_832_000_000,
            "revenue_usd_billions": 281.724,
            "net_income_usd_billions": 101.832,
        },
    ]

    result = calculate_growth(data)

    assert result[0]["fiscal_year"] == 2025
    assert result[0]["revenue_growth_pct"] == 14.93
    assert result[0]["net_income_growth_pct"] == 15.54

    assert result[1]["fiscal_year"] == 2024
    assert result[1]["revenue_growth_pct"] is None


def test_single_year_has_no_growth():
    data = [
        {
            "fiscal_year": 2025,
            "revenue_usd": 100_000_000_000,
            "net_income_usd": 20_000_000_000,
            "revenue_usd_billions": 100.0,
            "net_income_usd_billions": 20.0,
        }
    ]

    result = calculate_growth(data)

    assert result[0]["revenue_growth_pct"] is None
    assert result[0]["net_income_growth_pct"] is None
