
def calculate_growth(financials: list[dict]) -> list[dict]:
    """
    Calculate year-over-year revenue and net income growth.
    Input: annual financial records sorted newest to oldest.
    """
    ordered = sorted(
        financials,
        key=lambda row: row["fiscal_year"],
    )

    results = []

    for index, current in enumerate(ordered):
        previous = ordered[index - 1] if index > 0 else None

        revenue_growth = None
        income_growth = None

        if previous:
            old_revenue = previous["revenue_usd"]
            old_income = previous["net_income_usd"]

            if old_revenue:
                revenue_growth = round(
                    (
                        current["revenue_usd"] - old_revenue
                    ) / old_revenue * 100,
                    2,
                )

            if old_income:
                income_growth = round(
                    (
                        current["net_income_usd"] - old_income
                    ) / abs(old_income) * 100,
                    2,
                )

        results.append({
            "fiscal_year": current["fiscal_year"],
            "revenue_usd_billions": current["revenue_usd_billions"],
            "net_income_usd_billions": current["net_income_usd_billions"],
            "revenue_growth_pct": revenue_growth,
            "net_income_growth_pct": income_growth,
        })

    return sorted(
        results,
        key=lambda row: row["fiscal_year"],
        reverse=True,
    )
