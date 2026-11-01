import asyncio

import httpx
import pytest
from fastapi import HTTPException

from backend.app import sec


def make_observation(
    start,
    end,
    filed,
    accession,
    value,
    fy,
):
    return {
        "form": "10-K",
        "fp": "FY",
        "start": start,
        "end": end,
        "filed": filed,
        "accn": accession,
        "val": value,
        "fy": fy,
    }


def make_company_facts(
    revenue_items,
    income_items,
    entity_name="MICROSOFT CORPORATION",
):
    return {
        "entityName": entity_name,
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": revenue_items}
                },
                "NetIncomeLoss": {
                    "units": {"USD": income_items}
                },
            }
        },
    }


def test_get_annual_values_preserves_different_accessions():
    observations = [
        make_observation(
            "2023-07-01",
            "2024-06-30",
            "2024-07-30",
            "0001193125-24-000001",
            100_000_000_000,
            2024,
        ),
        make_observation(
            "2023-07-01",
            "2024-06-30",
            "2026-07-29",
            "0001193125-26-000001",
            110_000_000_000,
            2026,
        ),
    ]

    tag, records = sec.get_annual_values(
        {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"USD": observations}
            }
        },
        sec.REVENUE_TAGS,
    )

    assert tag == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert len(records) == 2

    assert {
        record["accession_number"]
        for record in records
    } == {
        "0001193125-24-000001",
        "0001193125-26-000001",
    }

    assert all(record["fiscal_year"] == 2024 for record in records)


def test_fetch_matches_latest_common_filing(monkeypatch):
    revenue_items = [
        make_observation(
            "2023-07-01",
            "2024-06-30",
            "2024-07-30",
            "0001193125-24-000001",
            100_000_000_000,
            2024,
        ),
        make_observation(
            "2023-07-01",
            "2024-06-30",
            "2026-07-29",
            "0001193125-26-000001",
            110_000_000_000,
            2026,
        ),
    ]

    income_items = [
        make_observation(
            "2023-07-01",
            "2024-06-30",
            "2024-07-30",
            "0001193125-24-000001",
            20_000_000_000,
            2024,
        ),
        make_observation(
            "2023-07-01",
            "2024-06-30",
            "2026-07-29",
            "0001193125-26-000002",
            25_000_000_000,
            2026,
        ),
    ]

    async def fake_fetch_company_facts(ticker="MSFT"):
        return make_company_facts(revenue_items, income_items)

    monkeypatch.setattr(
        sec,
        "fetch_company_facts",
        fake_fetch_company_facts,
    )

    result = asyncio.run(sec.fetch_microsoft_financials())

    assert len(result["annual_financials"]) == 1

    row = result["annual_financials"][0]

    # Only the older filing contains both metrics.
    assert row["revenue_accession_number"] == "0001193125-24-000001"
    assert row["income_accession_number"] == "0001193125-24-000001"
    assert row["source_accession_number"] == "0001193125-24-000001"

    assert row["revenue_usd"] == 100_000_000_000
    assert row["net_income_usd"] == 20_000_000_000

    assert row["source_filing"] == (
        "https://www.sec.gov/Archives/edgar/data/"
        "789019/000119312524000001/"
    )


def test_fetch_rejects_different_accessions(monkeypatch):
    revenue_items = [
        make_observation(
            "2023-07-01",
            "2024-06-30",
            "2024-07-30",
            "0001193125-24-000001",
            100_000_000_000,
            2024,
        )
    ]

    income_items = [
        make_observation(
            "2023-07-01",
            "2024-06-30",
            "2024-07-30",
            "0001193125-24-000002",
            20_000_000_000,
            2024,
        )
    ]

    async def fake_fetch_company_facts(ticker="MSFT"):
        return make_company_facts(revenue_items, income_items)

    monkeypatch.setattr(
        sec,
        "fetch_company_facts",
        fake_fetch_company_facts,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(sec.fetch_microsoft_financials())

    assert exc_info.value.status_code == 502


@pytest.mark.parametrize(
    ("ticker", "expected_cik"),
    [
        ("MSFT", "0000789019"),
        ("AAPL", "0000320193"),
        ("NVDA", "0001045810"),
        ("AMZN", "0001018724"),
        ("GOOGL", "0001652044"),
    ],
)
def test_ticker_resolves_to_expected_cik(ticker, expected_cik):
    normalized, company = sec.get_company_config(ticker.lower())

    assert normalized == ticker
    assert company["cik"] == expected_cik


def test_fetches_company_facts_for_two_tickers_with_mock_sec(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "ThesisLens tests test@example.com")
    requests = []
    original_client = httpx.AsyncClient

    def handler(request):
        requests.append(str(request.url))
        ticker = next(
            ticker for ticker, config in sec.SUPPORTED_COMPANIES.items()
            if f"CIK{config['cik']}.json" in str(request.url)
        )
        sequence = list(sec.SUPPORTED_COMPANIES).index(ticker) + 1
        accession = f"0001193125-24-{sequence:06d}"
        revenue = make_observation(
            "2023-07-01", "2024-06-30", "2024-07-30",
            accession, 100_000_000_000, 2024,
        )
        income = make_observation(
            "2023-07-01", "2024-06-30", "2024-07-30",
            accession, 20_000_000_000, 2024,
        )
        return httpx.Response(
            200,
            json=make_company_facts(
                [revenue], [income], sec.SUPPORTED_COMPANIES[ticker]["name"].upper(),
            ),
        )

    def mock_client(*args, **kwargs):
        return original_client(
            *args,
            transport=httpx.MockTransport(handler),
            **kwargs,
        )

    monkeypatch.setattr(sec.httpx, "AsyncClient", mock_client)

    microsoft = asyncio.run(sec.fetch_company_financials("MSFT"))
    apple = asyncio.run(sec.fetch_company_financials("AAPL"))

    assert microsoft["cik"] == "0000789019"
    assert apple["cik"] == "0000320193"
    assert microsoft["annual_financials"][0]["source_filing"].startswith(
        "https://www.sec.gov/Archives/edgar/data/789019/"
    )
    assert apple["annual_financials"][0]["source_filing"].startswith(
        "https://www.sec.gov/Archives/edgar/data/320193/"
    )
    assert any("CIK0000789019.json" in url for url in requests)
    assert any("CIK0000320193.json" in url for url in requests)


def test_unsupported_ticker_is_rejected_before_sec_request():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(sec.fetch_company_financials("NOPE"))

    assert exc_info.value.status_code == 404
    assert "Unsupported ticker" in exc_info.value.detail
