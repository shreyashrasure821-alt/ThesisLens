import pytest

from backend.app.evidence import build_evidence_report


def make_financial_record(year, revenue, income):
    accession = f"0001193125-{year % 100:02d}-000001"

    return {
        "fiscal_year": year,
        "revenue_usd": revenue,
        "net_income_usd": income,
        "revenue_usd_billions": revenue / 1_000_000_000,
        "net_income_usd_billions": income / 1_000_000_000,
        "revenue_filed_date": f"{year + 1}-07-30",
        "income_filed_date": f"{year + 1}-07-30",
        "source_accession_number": accession,
        "source_filing": (
            "https://www.sec.gov/Archives/edgar/data/"
            f"789019/{accession.replace('-', '')}/"
        ),
    }


def make_thesis(categories, claim_text="Test investment claim"):
    return {
        "claims": [{
            "claim_id": "C1",
            "claim_text": claim_text,
            "categories": categories,
        }]
    }


def test_revenue_claim_gets_historical_evidence():
    financials = [
        make_financial_record(2024, 100_000_000_000, 10_000_000_000),
        make_financial_record(2025, 120_000_000_000, 15_000_000_000),
    ]

    result = build_evidence_report(
        make_thesis(["revenue"]),
        financials,
    )

    claim = result["claims"][0]
    evidence = claim["evidence"][0]

    assert claim["evidence_status"] == "historical_context_available"
    assert evidence["metric"] == "annual_revenue_growth"
    assert evidence["value_pct"] == 20.0
    assert evidence["signal"] == "positive_historical_trend"
    assert evidence["sources"][0]["accession_number"]


def test_ai_and_revenue_claim_gets_partial_coverage():
    financials = [
        make_financial_record(2024, 100_000_000_000, 10_000_000_000),
        make_financial_record(2025, 120_000_000_000, 15_000_000_000),
    ]

    result = build_evidence_report(
        make_thesis(["revenue", "ai"]),
        financials,
    )

    claim = result["claims"][0]

    assert claim["evidence_status"] == "partial_coverage"
    assert len(claim["evidence"]) == 1
    assert claim["unsupported_categories"] == ["ai"]
    assert "ai" in result["unavailable_categories"]


def test_profitability_claim_calculates_margin():
    financials = [
        make_financial_record(2024, 100_000_000_000, 10_000_000_000),
        make_financial_record(2025, 120_000_000_000, 18_000_000_000),
    ]

    result = build_evidence_report(
        make_thesis(["profitability"]),
        financials,
    )

    claim = result["claims"][0]

    assert claim["evidence_status"] == "historical_context_available"
    assert len(claim["evidence"]) == 2

    margin = next(
        item for item in claim["evidence"]
        if item["metric"] == "net_income_margin"
    )

    assert margin["value_pct"] == 15.0
    assert margin["change_percentage_points"] == 5.0
    assert margin["signal"] == "positive_historical_trend"


def test_unsupported_claim_reports_insufficient_evidence():
    financials = [
        make_financial_record(2024, 100_000_000_000, 10_000_000_000),
        make_financial_record(2025, 120_000_000_000, 15_000_000_000),
    ]

    result = build_evidence_report(
        make_thesis(["ai", "cloud", "valuation"]),
        financials,
    )

    claim = result["claims"][0]

    assert claim["evidence_status"] == "insufficient_evidence"
    assert claim["evidence"] == []
    assert set(claim["unsupported_categories"]) == {
        "ai",
        "cloud",
        "valuation",
    }


def test_empty_financial_data_is_rejected():
    with pytest.raises(ValueError):
        build_evidence_report(
            make_thesis(["revenue"]),
            [],
        )


def test_positive_revenue_trend_supports_positive_historical_claim():
    financials = [
        make_financial_record(2024, 100_000_000_000, 10_000_000_000),
        make_financial_record(2025, 120_000_000_000, 15_000_000_000),
    ]

    claim = build_evidence_report(
        make_thesis(["revenue"], "Revenue is growing"), financials,
    )["claims"][0]["evidence"][0]

    assert claim["direction"] == "supporting"
    assert claim["metric"] == "annual_revenue_growth"
    assert claim["value_pct"] == 20.0
    assert claim["fiscal_year"] == 2025
    assert "company-wide annual revenue" in claim["description"]
    assert "does not establish future performance" in claim["interpretation"]
    assert claim["sources"][0]["url"].startswith("https://www.sec.gov/")


def test_negative_revenue_trend_contradicts_positive_historical_claim():
    financials = [
        make_financial_record(2024, 120_000_000_000, 15_000_000_000),
        make_financial_record(2025, 100_000_000_000, 12_000_000_000),
    ]

    claim = build_evidence_report(
        make_thesis(["revenue"], "Revenue is growing"), financials,
    )["claims"][0]["evidence"][0]

    assert claim["direction"] == "contradicting"
    assert claim["value_pct"] == pytest.approx(-16.67)
    assert "may weaken it" in claim["interpretation"]


def test_ambiguous_claim_gets_neutral_contextual_evidence():
    financials = [
        make_financial_record(2024, 100_000_000_000, 10_000_000_000),
        make_financial_record(2025, 120_000_000_000, 15_000_000_000),
    ]

    claim = build_evidence_report(
        make_thesis(["revenue"], "Revenue is an important business metric"),
        financials,
    )["claims"][0]["evidence"][0]

    assert claim["direction"] == "neutral"
    assert "contextual" in claim["interpretation"]


def test_future_facing_claim_is_not_marked_as_supported_by_history():
    financials = [
        make_financial_record(2024, 100_000_000_000, 10_000_000_000),
        make_financial_record(2025, 120_000_000_000, 15_000_000_000),
    ]

    claim = build_evidence_report(
        make_thesis(["revenue"], "Revenue will continue growing"), financials,
    )["claims"][0]["evidence"][0]

    assert claim["direction"] == "neutral"
    assert "cannot establish a future outcome" in claim["interpretation"]


def test_missing_metrics_and_sources_are_explicitly_insufficient():
    financials = [
        make_financial_record(2024, 100, 10),
        make_financial_record(2025, 120, 12),
    ]
    for record in financials:
        record.pop("revenue_usd")
        record.pop("revenue_filed_date")
        record.pop("source_accession_number")
        record.pop("source_filing")

    report = build_evidence_report(
        make_thesis(["revenue"], "Revenue is growing"), financials,
    )
    claim = report["claims"][0]
    evidence = claim["evidence"][0]

    assert claim["evidence_status"] == "insufficient_evidence"
    assert evidence["value_pct"] is None
    assert evidence["direction"] == "neutral"
    assert "unavailable" in evidence["interpretation"]
    assert evidence["sources"] == []


def test_missing_revenue_with_profitability_data_is_partial_coverage():
    financials = [
        make_financial_record(2024, 100, 10),
        make_financial_record(2025, 120, 15),
    ]
    for record in financials:
        record.pop("revenue_usd")

    claim = build_evidence_report(
        make_thesis(["revenue", "profitability"], "Revenue and profit are growing"),
        financials,
    )["claims"][0]

    assert claim["evidence_status"] == "partial_coverage"
    assert claim["evidence"][0]["value_pct"] is None
    assert claim["evidence"][1]["direction"] == "supporting"
