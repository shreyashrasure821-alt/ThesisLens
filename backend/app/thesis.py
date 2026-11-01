import re


CATEGORY_PATTERNS = {
    "revenue": [
        r"\brevenue\b",
        r"\bsales\b",
        r"\btop[- ]line\b",
        r"\bbookings\b",
        r"\bARR\b",
    ],
    "profitability": [
        r"\bprofit(?:ability)?\b",
        r"\bmargin(?:s)?\b",
        r"\bnet income\b",
        r"\boperating income\b",
        r"\bearnings\b",
        r"\bcash flow\b",
    ],
    "cloud": [
        r"\bcloud\b",
        r"\bAzure\b",
    ],
    "ai": [
        r"\bAI\b",
        r"\bartificial intelligence\b",
        r"\bgenerative AI\b",
        r"\bCopilot\b",
        r"\bmachine learning\b",
    ],
    "valuation": [
        r"\bvaluation\b",
        r"\bvalued\b",
        r"\bundervalued\b",
        r"\bovervalued\b",
        r"\bP/E\b",
        r"\bprice[- ]to[- ]earnings\b",
        r"\bEV/EBITDA\b",
        r"\bmarket capitalization\b",
    ],
    "competition": [
        r"\bcompetition\b",
        r"\bcompetitor(?:s)?\b",
        r"\bmarket share\b",
        r"\bcompetitive advantage\b",
    ],
    "risk": [
        r"\brisk(?:s)?\b",
        r"\bregulation\b",
        r"\bregulatory\b",
        r"\blitigation\b",
        r"\blawsuit(?:s)?\b",
        r"\bcybersecurity\b",
        r"\bthreat(?:s)?\b",
    ],
    "debt_liquidity": [
        r"\bdebt\b",
        r"\bliquidity\b",
        r"\bleverage\b",
        r"\bbalance sheet\b",
        r"\bcash reserves\b",
    ],
}


CATEGORY_EVIDENCE = {
    "revenue": [
        "Annual revenue from company filings",
        "Year-over-year revenue growth",
        "Segment-level revenue and growth, where disclosed",
    ],
    "profitability": [
        "Net income and operating income from company filings",
        "Gross and operating margin trends",
        "Cash flow from operations and free cash flow",
    ],
    "cloud": [
        "Cloud segment revenue and growth, where disclosed",
        "Cloud segment operating income or margins, where disclosed",
        "Management disclosures about cloud demand and adoption",
    ],
    "ai": [
        "AI product adoption and AI-related revenue, where disclosed",
        "Capital expenditure and AI infrastructure investment",
        "Company disclosures about AI demand and monetization",
    ],
    "valuation": [
        "Current share price and market capitalization",
        "Valuation multiples such as P/E and EV/EBITDA",
        "Earnings and cash-flow metrics",
        "Comparable-company valuation data",
    ],
    "competition": [
        "Competitor disclosures and market-share data",
        "Comparable product, pricing, and growth information",
        "Credible independent industry research",
    ],
    "risk": [
        "Risk factors in company filings",
        "Material litigation and regulatory disclosures",
        "Operational, customer concentration, and competitive risks",
    ],
    "debt_liquidity": [
        "Balance sheet debt and cash balances",
        "Debt maturities and interest expense",
        "Liquidity and cash-flow coverage",
    ],
    "general": [
        "Relevant company filings and investor disclosures",
        "Independent industry and market sources",
        "Evidence directly testing the claim's assumptions",
    ],
}


def split_into_claims(thesis: str) -> list[str]:
    """
    Split a thesis into sentence-level or bullet-level claims.
    """

    parts = re.split(
        r"(?<=[.!?])\s+|\r?\n+|;\s*",
        thesis.strip(),
    )

    claims = []
    seen = set()

    for part in parts:
        claim = re.sub(
            r"^\s*(?:[-*•]|\d+[.)])\s*",
            "",
            part,
        ).strip()

        claim = claim.rstrip(".!?; ").strip()

        if not claim:
            continue

        normalized = claim.casefold()

        if normalized not in seen:
            claims.append(claim)
            seen.add(normalized)

    return claims


def classify_claim(claim: str) -> list[str]:
    """
    Assign one or more topic categories using keyword matching.
    """

    categories = []

    for category, patterns in CATEGORY_PATTERNS.items():
        if any(
            re.search(pattern, claim, re.IGNORECASE)
            for pattern in patterns
        ):
            categories.append(category)

    return categories or ["general"]


def analyze_thesis(thesis: str) -> dict:
    """
    Decompose an investment thesis into testable claims.

    This is a rule-based first version.
    It does not verify claims or issue investment recommendations.
    """

    if not isinstance(thesis, str) or not thesis.strip():
        raise ValueError("Thesis cannot be empty.")

    cleaned_thesis = thesis.strip()

    if len(cleaned_thesis) > 4000:
        raise ValueError("Thesis cannot exceed 4000 characters.")

    claim_texts = split_into_claims(cleaned_thesis)

    if not claim_texts:
        raise ValueError("No valid claims could be extracted.")

    claims = []

    for index, claim_text in enumerate(claim_texts, start=1):
        categories = classify_claim(claim_text)

        evidence_required = []

        for category in categories:
            evidence_required.extend(
                CATEGORY_EVIDENCE[category]
            )

        # Remove duplicate evidence requirements.
        evidence_required = list(dict.fromkeys(evidence_required))

        claims.append({
            "claim_id": f"C{index}",
            "claim_text": claim_text,
            "categories": categories,
            "evidence_required": evidence_required,
            "status": "pending_evidence",
        })

    return {
        "thesis": cleaned_thesis,
        "analysis_method": "rule_based_keyword_classification",
        "claim_count": len(claims),
        "claims": claims,
        "limitations": (
            "Claims are extracted using sentence and bullet splitting "
            "with keyword-based classification. A sentence may receive "
            "multiple categories. Claims have not been fact-checked, "
            "and no investment verdict is produced."
        ),
    }