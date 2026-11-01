"""Summarize evidence coverage for a decomposed investment thesis."""


_FULL = "historical_context_available"
_PARTIAL = "partial_coverage"
_INSUFFICIENT = "insufficient_evidence"


def build_thesis_assessment(evidence_report: dict) -> dict:
    """Classify claim coverage and describe the remaining research gaps.

    This assesses coverage of the supplied evidence report; it does not
    verify whether the underlying investment thesis is true.
    """
    claims = evidence_report.get("claims") if isinstance(evidence_report, dict) else None
    if not isinstance(claims, list) or not claims:
        raise ValueError("Evidence report must contain a non-empty claims list.")

    counts = {_FULL: 0, _PARTIAL: 0, _INSUFFICIENT: 0}
    unsupported_categories = []
    seen_categories = set()

    for claim in claims:
        status = claim.get("evidence_status")
        if status not in counts:
            raise ValueError(f"Unknown evidence status: {status!r}.")
        counts[status] += 1
        for category in claim.get("unsupported_categories", []):
            if category not in seen_categories:
                seen_categories.add(category)
                unsupported_categories.append(category)

    total = len(claims)
    with_context = counts[_FULL]
    partial = counts[_PARTIAL]
    insufficient = counts[_INSUFFICIENT]

    if with_context == total:
        overall = "full_historical_coverage"
    elif with_context + partial:
        overall = "partial_coverage"
    else:
        overall = "insufficient_evidence"

    research_gaps = [
        {
            "category": category,
            "gap": (
                f"Historical evidence for '{category}' is not available in "
                "the current evidence report; a suitable verified data "
                "source is needed to assess this claim category."
            ),
        }
        for category in unsupported_categories
    ]

    assessment_summary = (
        f"The report assessed {total} claim(s): {with_context} have full "
        f"historical context, {partial} have partial coverage, and "
        f"{insufficient} have insufficient evidence. Overall coverage is "
        f"{overall.replace('_', ' ')}."
    )

    return {
        "overall_coverage": overall,
        "total_claims": total,
        "claims_with_historical_context": with_context,
        "partially_covered_claims": partial,
        "claims_with_insufficient_evidence": insufficient,
        "unsupported_categories": unsupported_categories,
        "research_gaps": research_gaps,
        "limitations": [
            "Coverage describes how much of each claim is addressed by the evidence currently supplied.",
            "Historical financial context does not verify the investment thesis or establish future performance.",
            "A claim can require additional evidence beyond the categories represented in this report.",
        ],
        "assessment_summary": assessment_summary,
    }
