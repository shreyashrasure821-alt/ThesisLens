import pytest

from backend.app.thesis import (
    analyze_thesis,
    classify_claim,
    split_into_claims,
)


def test_split_thesis_into_sentences_and_bullets():
    thesis = (
        "Microsoft revenue is growing.\n"
        "- Azure cloud demand is strong.\n"
        "3. AI adoption is increasing."
    )

    claims = split_into_claims(thesis)

    assert len(claims) == 3
    assert claims[0] == "Microsoft revenue is growing"
    assert claims[1] == "Azure cloud demand is strong"
    assert claims[2] == "AI adoption is increasing"


def test_classify_multiple_categories():
    claim = (
        "Microsoft's AI and cloud businesses "
        "will increase revenue."
    )

    categories = classify_claim(claim)

    assert "ai" in categories
    assert "cloud" in categories
    assert "revenue" in categories


def test_unrecognized_claim_gets_general_category():
    categories = classify_claim(
        "Microsoft has a durable long-term future."
    )

    assert categories == ["general"]


def test_analyze_thesis_creates_pending_claims():
    result = analyze_thesis(
        "Microsoft revenue is growing. "
        "Its AI business is expanding."
    )

    assert result["claim_count"] == 2
    assert result["analysis_method"] == (
        "rule_based_keyword_classification"
    )

    for claim in result["claims"]:
        assert claim["claim_id"]
        assert claim["categories"]
        assert claim["evidence_required"]
        assert claim["status"] == "pending_evidence"


def test_empty_thesis_is_rejected():
    with pytest.raises(ValueError):
        analyze_thesis("   ")