import re


SUPPORTED_CATEGORIES = {
    "revenue",
    "profitability",
}

_POSITIVE_TERMS = re.compile(
    r"\b(grow(?:ing|s|th)?|increas(?:e|es|ed|ing)|rise|rises|rose|"
    r"expand(?:s|ed|ing)?|improv(?:e|es|ed|ing)|strengthen(?:s|ed|ing)?|"
    r"higher|accelerat(?:e|es|ed|ing)|strong|robust|profitable|positive)\b",
    re.IGNORECASE,
)
_NEGATIVE_TERMS = re.compile(
    r"\b(declin(?:e|es|ed|ing)|fall(?:s|en|ing)?|decreas(?:e|es|ed|ing)|"
    r"drop(?:s|ped|ping)?|contract(?:s|ed|ing)?|shrink(?:s|ank|ing)?|"
    r"worsen(?:s|ed|ing)?|weaken(?:s|ed|ing)?|lower|decelerate|"
    r"slow(?:s|ed|ing)?|not\s+(?:grow|growing|grown|increase|increasing|improve|improving)|"
    r"no\s+growth|negative|unprofitable|loss(?:es)?)\b",
    re.IGNORECASE,
)
_FUTURE_TERMS = re.compile(
    r"\b(will|would|expect(?:s|ed)?|forecast(?:s|ed)?|project(?:s|ed)?|"
    r"future|next|upcoming|by\s+20\d{2})\b",
    re.IGNORECASE,
)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _get_signal(value: float | None) -> str:
    if value is None:
        return "not_available"
    if value > 0:
        return "positive_historical_trend"
    if value < 0:
        return "negative_historical_trend"
    return "flat_historical_trend"


def _growth_by_year(records: list[dict], metric: str) -> dict[int, float | None]:
    """Calculate year-over-year change only where both values are usable."""
    result = {}
    for index, current in enumerate(records):
        change = None
        if index:
            previous = records[index - 1]
            current_value = current.get(metric)
            previous_value = previous.get(metric)
            if (
                _is_number(current_value)
                and _is_number(previous_value)
                and previous_value != 0
            ):
                denominator = (
                    abs(previous_value) if metric == "net_income_usd"
                    else previous_value
                )
                change = round(
                    (current_value - previous_value) / denominator * 100,
                    2,
                )
        result[current["fiscal_year"]] = change
    return result


def _claim_target(claim_text: str, category: str) -> int | None:
    """Return 1/-1 for clear positive/negative trend language; else None."""
    category_terms = {
        "revenue": re.compile(
            r"\b(revenue|sales|top[- ]line|bookings|ARR)\b", re.IGNORECASE
        ),
        "profitability": re.compile(
            r"\b(profit(?:ability)?|margin|net income|operating income|"
            r"earnings|cash flow)\b", re.IGNORECASE
        ),
    }
    clauses = re.split(r"\b(?:but|while|whereas|although|however)\b|[,;]", claim_text, flags=re.IGNORECASE)
    relevant = [
        clause for clause in clauses
        if category in category_terms and category_terms[category].search(clause)
    ]
    text = " ".join(relevant) if relevant else claim_text
    if _NEGATIVE_TERMS.search(text):
        return -1
    if _POSITIVE_TERMS.search(text):
        return 1
    return None


def _direction_and_explanation(
    value: float | None,
    target: int | None,
    claim_text: str,
    metric_label: str,
) -> tuple[str, str]:
    if value is None:
        return (
            "neutral",
            f"Comparable historical {metric_label} data is unavailable, so this metric cannot support or contradict the claim.",
        )

    if _FUTURE_TERMS.search(claim_text):
        return (
            "neutral",
            f"This is a historical {metric_label} trend. It provides context but cannot establish a future outcome.",
        )

    if target is None or value == 0:
        reason = (
            "The observed historical trend is flat."
            if value == 0
            else "The claim does not state a clear direction for this metric."
        )
        return (
            "neutral",
            f"{reason} The metric is contextual and does not directly prove or disprove the claim.",
        )

    if (value > 0 and target > 0) or (value < 0 and target < 0):
        return (
            "supporting",
            f"The historical {metric_label} trend moves in the direction stated by the claim; it does not establish future performance.",
        )

    return (
        "contradicting",
        f"The historical {metric_label} trend moves against the direction stated by the claim and may weaken it; it does not establish future performance.",
    )


def build_evidence_report(
    thesis_analysis: dict,
    annual_financials: list[dict],
    company: str = "MICROSOFT CORPORATION",
) -> dict:
    """Build historical evidence without treating it as a future prediction."""
    if not annual_financials:
        raise ValueError("Annual financial data is required.")
    if not thesis_analysis.get("claims"):
        raise ValueError("Thesis claims are required.")

    ordered = sorted(annual_financials, key=lambda row: row["fiscal_year"])
    revenue_growth = _growth_by_year(ordered, "revenue_usd")
    income_growth = _growth_by_year(ordered, "net_income_usd")
    latest = ordered[-1]
    previous = ordered[-2] if len(ordered) > 1 else None
    latest_year = latest["fiscal_year"]

    latest_margin = None
    previous_margin = None
    margin_change = None
    if (
        _is_number(latest.get("revenue_usd"))
        and latest["revenue_usd"] != 0
        and _is_number(latest.get("net_income_usd"))
    ):
        latest_margin = round(
            latest["net_income_usd"] / latest["revenue_usd"] * 100, 2
        )
    if (
        previous
        and _is_number(previous.get("revenue_usd"))
        and previous["revenue_usd"] != 0
        and _is_number(previous.get("net_income_usd"))
    ):
        previous_margin = round(
            previous["net_income_usd"] / previous["revenue_usd"] * 100, 2
        )
        if latest_margin is not None:
            margin_change = round(latest_margin - previous_margin, 2)

    def make_source(record: dict) -> dict | None:
        source = {
            "fiscal_year": record.get("fiscal_year"),
            "filed_date": record.get("revenue_filed_date"),
            "accession_number": record.get("source_accession_number"),
            "url": record.get("source_filing"),
        }
        return source if any(
            source[key] for key in ("filed_date", "accession_number", "url")
        ) else None

    sources = [
        source for record in (latest, previous)
        if record is not None
        if (source := make_source(record)) is not None
    ]

    claim_reports = []
    unavailable_categories = set()

    for claim in thesis_analysis["claims"]:
        categories = claim.get("categories", [])
        claim_text = claim.get("claim_text", "")
        evidence = []
        unsupported = []

        def add_evidence(
            evidence_id: str,
            metric: str,
            description: str,
            value: float | None,
            direction_value: float | None,
            metric_label: str,
            **extra,
        ):
            direction, explanation = _direction_and_explanation(
                direction_value, target, claim_text, metric_label
            )
            evidence.append({
                "evidence_id": evidence_id,
                "description": description,
                "direction": direction,
                "metric": metric,
                "fiscal_year": latest_year,
                "value_pct": value,
                "signal": _get_signal(direction_value),
                "interpretation": explanation,
                "sources": sources,
                **extra,
            })

        for category in categories:
            if category == "revenue":
                target = _claim_target(claim_text, category)
                growth = revenue_growth.get(latest_year)
                add_evidence(
                    "E_REVENUE_01",
                    "annual_revenue_growth",
                    "Year-over-year change in company-wide annual revenue.",
                    growth,
                    growth,
                    "revenue growth",
                )
            elif category == "profitability":
                target = _claim_target(claim_text, category)
                growth = income_growth.get(latest_year)
                add_evidence(
                    "E_PROFIT_01",
                    "annual_net_income_growth",
                    "Year-over-year change in annual net income.",
                    growth,
                    growth,
                    "net income growth",
                )
                add_evidence(
                    "E_PROFIT_02",
                    "net_income_margin",
                    "Net income as a percentage of company-wide revenue.",
                    latest_margin,
                    margin_change,
                    "net income margin change",
                    change_percentage_points=margin_change,
                )
            else:
                unsupported.append(category)
                unavailable_categories.add(category)

        available_categories = set()
        if "revenue" in categories and revenue_growth.get(latest_year) is not None:
            available_categories.add("revenue")
        if "profitability" in categories and (
            income_growth.get(latest_year) is not None or margin_change is not None
        ):
            available_categories.add("profitability")

        if not available_categories:
            status = "insufficient_evidence"
        elif (
            unsupported
            or available_categories != (set(categories) & SUPPORTED_CATEGORIES)
        ):
            status = "partial_coverage"
        elif evidence:
            status = "historical_context_available"
        else:
            status = "insufficient_evidence"

        claim_reports.append({
            "claim_id": claim["claim_id"],
            "claim_text": claim_text,
            "categories": categories,
            "evidence_status": status,
            "evidence": evidence,
            "unsupported_categories": unsupported,
        })

    return {
        "company": company,
        "evidence_method": "historical_sec_financial_analysis",
        "periods_available": [row["fiscal_year"] for row in reversed(ordered)],
        "supported_categories": sorted(SUPPORTED_CATEGORIES),
        "unavailable_categories": sorted(unavailable_categories),
        "claims": claim_reports,
        "limitations": [
            "Only annual revenue and net income data are currently used.",
            "Historical trends do not prove future performance.",
            "Company-wide revenue does not establish AI or cloud segment growth.",
            "Net income margin alone does not fully measure profitability quality.",
            "Unsupported categories require additional verified data sources.",
        ],
    }
