import asyncio

import pytest
from fastapi import HTTPException

from backend.app import main
from backend.app.evidence import build_evidence_report


def test_thesis_evidence_endpoint(monkeypatch):
    financial_data = {
        "annual_financials": [
            {
                "fiscal_year": 2024,
                "revenue_usd": 100_000_000_000,
                "net_income_usd": 10_000_000_000,
                "revenue_usd_billions": 100.0,
                "net_income_usd_billions": 10.0,
                "revenue_filed_date": "2024-07-30",
                "income_filed_date": "2024-07-30",
                "source_accession_number": "0001193125-24-000001",
                "source_filing": "https://www.sec.gov/example-2024",
            },
            {
                "fiscal_year": 2025,
                "revenue_usd": 120_000_000_000,
                "net_income_usd": 15_000_000_000,
                "revenue_usd_billions": 120.0,
                "net_income_usd_billions": 15.0,
                "revenue_filed_date": "2025-07-30",
                "income_filed_date": "2025-07-30",
                "source_accession_number": "0001193125-25-000001",
                "source_filing": "https://www.sec.gov/example-2025",
            },
        ]
    }

    async def fake_fetch_microsoft_financials():
        return financial_data

    monkeypatch.setattr(
        main,
        "fetch_microsoft_financials",
        fake_fetch_microsoft_financials,
    )

    request = main.ThesisEvidenceRequest(
        thesis=(
            "Microsoft revenue is growing. "
            "Its AI business is expanding."
        )
    )

    result = asyncio.run(main.thesis_evidence(request))

    # Existing response payloads retain their original structures and values.
    assert set(result) == {
        "thesis_analysis", "evidence_report", "thesis_assessment",
    }
    expected_thesis = main.analyze_thesis(request.thesis)
    expected_evidence = build_evidence_report(
        expected_thesis,
        financial_data["annual_financials"],
    )
    assert result["thesis_analysis"] == expected_thesis
    assert result["evidence_report"] == expected_evidence
    assert set(result["evidence_report"]) == {
        "company", "evidence_method", "periods_available",
        "supported_categories", "unavailable_categories", "claims",
        "limitations",
    }
    assert result["thesis_analysis"]["claim_count"] == 2

    claims = result["evidence_report"]["claims"]

    assert claims[0]["evidence_status"] == "historical_context_available"
    assert claims[0]["evidence"][0]["direction"] == "supporting"
    assert claims[0]["evidence"][0]["description"]
    assert claims[1]["evidence_status"] == "insufficient_evidence"

    assert result["evidence_report"]["company"] == (
        "MICROSOFT CORPORATION"
    )
    assert "thesis_assessment" in result
    assessment = result["thesis_assessment"]
    assert assessment["total_claims"] == 2
    assert assessment["overall_coverage"] == "partial_coverage"


def test_company_analysis_uses_selected_company_data(monkeypatch):
    financial_data = {
        "company": "APPLE INC.",
        "currency": "USD",
        "source_api": "https://data.sec.gov/companyfacts/CIK0000320193.json",
        "methodology": "matched SEC annual filings",
        "annual_financials": [
            {
                "fiscal_year": 2023,
                "revenue_usd": 100_000_000_000,
                "net_income_usd": 10_000_000_000,
                "revenue_usd_billions": 100.0,
                "net_income_usd_billions": 10.0,
            },
            {
                "fiscal_year": 2024,
                "revenue_usd": 150_000_000_000,
                "net_income_usd": 20_000_000_000,
                "revenue_usd_billions": 150.0,
                "net_income_usd_billions": 20.0,
            },
        ],
    }
    requested = []

    async def fake_fetch_company_financials(ticker):
        requested.append(ticker)
        return financial_data

    monkeypatch.setattr(main, "fetch_company_financials", fake_fetch_company_financials)

    result = asyncio.run(main.company_analysis("AAPL"))

    assert requested == ["AAPL"]
    assert result["company"] == "APPLE INC."
    latest = result["analysis"][0]
    assert latest["revenue_growth_pct"] == 50.0
    assert latest["net_income_growth_pct"] == 100.0


def test_thesis_evidence_uses_selected_company(monkeypatch):
    financial_data = {
        "company": "APPLE INC.",
        "annual_financials": [
            {
                "fiscal_year": 2023,
                "revenue_usd": 100_000_000_000,
                "net_income_usd": 10_000_000_000,
                "revenue_usd_billions": 100.0,
                "net_income_usd_billions": 10.0,
                "revenue_filed_date": "2024-07-30",
                "source_accession_number": "0001193125-24-000001",
                "source_filing": "https://www.sec.gov/example-apple-2023",
            },
            {
                "fiscal_year": 2024,
                "revenue_usd": 150_000_000_000,
                "net_income_usd": 20_000_000_000,
                "revenue_usd_billions": 150.0,
                "net_income_usd_billions": 20.0,
                "revenue_filed_date": "2025-07-30",
                "source_accession_number": "0001193125-25-000001",
                "source_filing": "https://www.sec.gov/example-apple-2024",
            },
        ],
    }
    requested = []

    async def fake_fetch_company_financials(ticker):
        requested.append(ticker)
        return financial_data

    monkeypatch.setattr(main, "fetch_company_financials", fake_fetch_company_financials)
    request = main.ThesisEvidenceRequest(
        thesis="Apple revenue is growing.",
        ticker="AAPL",
    )

    result = asyncio.run(main.thesis_evidence(request))

    assert requested == ["AAPL"]
    assert result["evidence_report"]["company"] == "APPLE INC."
    revenue_item = result["evidence_report"]["claims"][0]["evidence"][0]
    assert revenue_item["value_pct"] == 50.0
    assert result["thesis_assessment"]["total_claims"] == 1


def test_evidence_endpoint_rejects_unsupported_ticker():
    request = main.ThesisEvidenceRequest(
        thesis="Company revenue will increase.",
        ticker="NOPE",
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(main.thesis_evidence(request))

    assert exc_info.value.status_code == 404
    assert "Unsupported ticker" in exc_info.value.detail
