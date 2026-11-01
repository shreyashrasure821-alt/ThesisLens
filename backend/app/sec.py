
import os
from datetime import date

import httpx
from fastapi import HTTPException

SEC_BASE_URL = "https://data.sec.gov"
SUPPORTED_COMPANIES = {
    "MSFT": {"name": "Microsoft Corporation", "cik": "0000789019"},
    "AAPL": {"name": "Apple Inc.", "cik": "0000320193"},
    "NVDA": {"name": "NVIDIA Corporation", "cik": "0001045810"},
    "AMZN": {"name": "Amazon.com, Inc.", "cik": "0001018724"},
    "GOOGL": {"name": "Alphabet Inc.", "cik": "0001652044"},
}
MICROSOFT_CIK = SUPPORTED_COMPANIES["MSFT"]["cik"]


def get_company_config(ticker: str) -> tuple[str, dict]:
    normalized = ticker.strip().upper() if isinstance(ticker, str) else ""
    company = SUPPORTED_COMPANIES.get(normalized)
    if company is None:
        supported = ", ".join(SUPPORTED_COMPANIES)
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported ticker '{ticker}'. Supported tickers: {supported}.",
        )
    return normalized, company

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]

NET_INCOME_TAGS = ["NetIncomeLoss"]


async def fetch_company_facts(ticker: str = "MSFT") -> dict:
    ticker, company = get_company_config(ticker)
    user_agent = os.getenv("SEC_USER_AGENT")

    if not user_agent or "@" not in user_agent:
        raise HTTPException(
            status_code=503,
            detail="Configure SEC_USER_AGENT with a contact email.",
        )

    url = (
        f"{SEC_BASE_URL}/api/xbrl/companyfacts/"
        f"CIK{company['cik']}.json"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": user_agent,
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"SEC returned HTTP {exc.response.status_code}.",
        ) from exc

    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve valid SEC data.",
        ) from exc

    if not data.get("facts", {}).get("us-gaap"):
        raise HTTPException(
            status_code=502,
            detail="SEC response is missing US-GAAP facts.",
        )

    return data




def get_annual_values(
    facts: dict,
    candidate_tags: list[str],
) -> tuple[str, list[dict]]:
    """
    Extract annual 10-K observations.

    Preserve observations by fiscal period end AND accession number
    so that different SEC filings are not mixed accidentally.
    """

    selected_tag = None
    selected_units = None

    for tag in candidate_tags:
        definition = facts.get(tag)

        if not definition:
            continue

        units = definition.get("units", {})

        if "USD" in units and units["USD"]:
            selected_tag = tag
            selected_units = units["USD"]
            break

    if not selected_tag:
        return "", []

    observations = {}

    for item in selected_units:
        if item.get("form") != "10-K":
            continue

        if item.get("fp") != "FY":
            continue

        start = item.get("start")
        end = item.get("end")
        filed = item.get("filed")
        accession = item.get("accn")
        fiscal_year = item.get("fy")

        if not all([start, end, filed, accession, fiscal_year]):
            continue

        if filed > date.today().isoformat():
            continue

        try:
            days = (
                date.fromisoformat(end)
                - date.fromisoformat(start)
            ).days
        except ValueError:
            continue

        if not 330 <= days <= 380:
            continue

        try:
            fiscal_year = int(end[:4])
            value = float(item["val"])
        except (ValueError, TypeError, KeyError):
            continue

        # Keep separate observations for different SEC filings.
        key = (end, accession)

        previous = observations.get(key)

        if previous is None or filed > previous["filed"]:
            observations[key] = {
                "fiscal_period_start": start,
                "fiscal_period_end": end,
                "fiscal_year": fiscal_year,
                "value_usd": value,
                "filed": filed,
                "form": "10-K",
                "accession_number": accession,
            }

    records = sorted(
        observations.values(),
        key=lambda row: (
            row["fiscal_period_end"],
            row["filed"],
        ),
        reverse=True,
    )

    return selected_tag, records

async def fetch_company_financials(ticker: str = "MSFT") -> dict:
    ticker, company = get_company_config(ticker)
    data = await fetch_company_facts(ticker)
    gaap = data["facts"]["us-gaap"]

    revenue_tag, revenues = get_annual_values(
        gaap, REVENUE_TAGS
    )

    income_tag, incomes = get_annual_values(
        gaap, NET_INCOME_TAGS
    )

    if not revenues or not incomes:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not find annual revenue and net income "
                "observations in the SEC company facts."
            ),
        )

    # Match using BOTH fiscal period end and SEC accession.
    income_by_key = {
        (
            row["fiscal_period_end"],
            row["accession_number"],
        ): row
        for row in incomes
    }

    matched_by_end = {}

    for revenue in revenues:
        key = (
            revenue["fiscal_period_end"],
            revenue["accession_number"],
        )

        income = income_by_key.get(key)

        if income is None:
            continue

        # An accession identifies one filing; its filing dates
        # should also agree for both observations.
        if revenue["filed"] != income["filed"]:
            continue

        period_end = revenue["fiscal_period_end"]

        previous = matched_by_end.get(period_end)

        if (
            previous is None
            or revenue["filed"] > previous["revenue"]["filed"]
        ):
            matched_by_end[period_end] = {
                "revenue": revenue,
                "income": income,
            }

    if not matched_by_end:
        raise HTTPException(
            status_code=502,
            detail=(
                "No matching annual revenue and net income "
                "observations from the same SEC filings were found."
            ),
        )

    cik = str(int(company["cik"]))
    results = []

    # Select the five most recent periods after matching.
    selected_periods = sorted(
        matched_by_end.keys(),
        reverse=True,
    )[:5]

    for period_end in selected_periods:
        matched = matched_by_end[period_end]

        revenue = matched["revenue"]
        income = matched["income"]

        accession = revenue["accession_number"]
        accession_path = accession.replace("-", "")

        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik}/{accession_path}/"
        )

        results.append({
            "fiscal_year": revenue["fiscal_year"],
            "period_start": revenue["fiscal_period_start"],
            "period_end": revenue["fiscal_period_end"],
            "revenue_usd": revenue["value_usd"],
            "revenue_usd_billions": round(
                revenue["value_usd"] / 1_000_000_000, 3
            ),
            "net_income_usd": income["value_usd"],
            "net_income_usd_billions": round(
                income["value_usd"] / 1_000_000_000, 3
            ),
            "revenue_filed_date": revenue["filed"],
            "income_filed_date": income["filed"],
            "revenue_accession_number": revenue["accession_number"],
            "income_accession_number": income["accession_number"],
            "source_accession_number": accession,
            "source_filing": filing_url,
        })

    return {
        "company": data.get("entityName", company["name"]),
        "cik": company["cik"],
        "currency": "USD",
        "units": {
            "revenue_usd": "USD",
            "net_income_usd": "USD",
            "revenue_usd_billions": "USD billions",
            "net_income_usd_billions": "USD billions",
        },
        "metric_tags": {
            "revenue": revenue_tag,
            "net_income": income_tag,
        },
        "methodology": (
            "Annual 10-K observations matched by fiscal period end "
            "and SEC accession number. Latest common filing selected "
            "per fiscal period."
        ),
        "source_api": (
            f"{SEC_BASE_URL}/api/xbrl/companyfacts/"
            f"CIK{company['cik']}.json"
        ),
        "annual_financials": results,
    }


async def fetch_microsoft_financials() -> dict:
    """Backward-compatible Microsoft-specific fetch wrapper."""
    return await fetch_company_financials("MSFT")
