from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.app.sec import (
    fetch_company_financials,
    fetch_microsoft_financials,
    get_company_config,
)
from backend.app.analysis import calculate_growth
from backend.app.thesis import analyze_thesis
from backend.app.evidence import build_evidence_report
from backend.app.assessment import build_thesis_assessment


app = FastAPI(
    title="ThesisLens API",
    description="Evidence-first investment research for learners.",
    version="0.1.0",
)


class ThesisAnalysisRequest(BaseModel):
    thesis: str = Field(
        min_length=10,
        max_length=4000,
        description="Investment thesis to decompose into claims.",
    )


class ThesisEvidenceRequest(ThesisAnalysisRequest):
    ticker: str = Field(default="MSFT", max_length=10)


@app.get("/")
def root():
    return {
        "app": "ThesisLens",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "thesislens-backend",
    }


@app.get("/api/companies/MSFT/financials")
async def microsoft_financials():
    return await fetch_microsoft_financials()


@app.get("/api/companies/{ticker}/financials")
async def company_financials(ticker: str):
    return await fetch_company_financials(ticker)


@app.get("/api/companies/MSFT/analysis")
async def microsoft_analysis():
    data = await fetch_microsoft_financials()

    financials = data["annual_financials"]
    growth = calculate_growth(financials)

    return {
        "company": data["company"],
        "currency": data["currency"],
        "source_api": data["source_api"],
        "methodology": data["methodology"],
        "analysis": growth,
    }


@app.get("/api/companies/{ticker}/analysis")
async def company_analysis(ticker: str):
    data = await fetch_company_financials(ticker)
    growth = calculate_growth(data["annual_financials"])

    return {
        "company": data["company"],
        "currency": data["currency"],
        "source_api": data["source_api"],
        "methodology": data["methodology"],
        "analysis": growth,
    }


@app.post("/api/thesis/analyze")
def thesis_analysis(request: ThesisAnalysisRequest):
    try:
        return analyze_thesis(request.thesis)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@app.post("/api/thesis/evidence")
async def thesis_evidence(request: ThesisEvidenceRequest):
    try:
        ticker, company_config = get_company_config(request.ticker)
        thesis_result = analyze_thesis(request.thesis)

        financial_data = (
            await fetch_microsoft_financials()
            if ticker == "MSFT"
            else await fetch_company_financials(ticker)
        )

        evidence_result = build_evidence_report(
            thesis_result,
            financial_data["annual_financials"],
            company=financial_data.get("company", company_config["name"].upper()),
        )
        assessment_result = build_thesis_assessment(evidence_result)

        return {
            "thesis_analysis": thesis_result,
            "evidence_report": evidence_result,
            "thesis_assessment": assessment_result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
