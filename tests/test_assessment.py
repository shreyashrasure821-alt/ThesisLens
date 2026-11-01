import pytest

from backend.app.assessment import build_thesis_assessment


def make_report(*claims):
    return {"claims": list(claims)}


def make_claim(status, unsupported=()):
    return {
        "evidence_status": status,
        "unsupported_categories": list(unsupported),
    }


def test_all_claims_have_historical_context():
    result = build_thesis_assessment(make_report(
        make_claim("historical_context_available"),
        make_claim("historical_context_available"),
    ))

    assert result["overall_coverage"] == "full_historical_coverage"
    assert result["total_claims"] == 2
    assert result["claims_with_historical_context"] == 2
    assert result["partially_covered_claims"] == 0
    assert result["claims_with_insufficient_evidence"] == 0


def test_mixed_coverage_counts_and_classification():
    result = build_thesis_assessment(make_report(
        make_claim("historical_context_available"),
        make_claim("partial_coverage", ["ai"]),
        make_claim("insufficient_evidence", ["valuation"]),
    ))

    assert result["overall_coverage"] == "partial_coverage"
    assert result["total_claims"] == 3
    assert result["claims_with_historical_context"] == 1
    assert result["partially_covered_claims"] == 1
    assert result["claims_with_insufficient_evidence"] == 1
    assert result["unsupported_categories"] == ["ai", "valuation"]


def test_all_claims_have_insufficient_evidence():
    result = build_thesis_assessment(make_report(
        make_claim("insufficient_evidence", ["valuation"]),
        make_claim("insufficient_evidence", ["ai"]),
    ))

    assert result["overall_coverage"] == "insufficient_evidence"
    assert result["claims_with_insufficient_evidence"] == 2
    assert [gap["category"] for gap in result["research_gaps"]] == [
        "valuation", "ai",
    ]
    assert all(gap["gap"] for gap in result["research_gaps"])


def test_unsupported_categories_are_aggregated_without_duplicates():
    result = build_thesis_assessment(make_report(
        make_claim("partial_coverage", ["ai", "cloud"]),
        make_claim("insufficient_evidence", ["ai", "valuation"]),
    ))

    assert result["unsupported_categories"] == ["ai", "cloud", "valuation"]
    assert [gap["category"] for gap in result["research_gaps"]] == [
        "ai", "cloud", "valuation",
    ]


def test_empty_claims_are_rejected():
    with pytest.raises(ValueError, match="non-empty claims list"):
        build_thesis_assessment({"claims": []})


def test_missing_claims_are_rejected():
    with pytest.raises(ValueError, match="non-empty claims list"):
        build_thesis_assessment({})
