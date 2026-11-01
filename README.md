# ThesisLens

ThesisLens is an evidence-first research tool that helps users compare an investment thesis with historical company financial data. It retrieves annual SEC CompanyFacts data, extracts selected revenue and profitability metrics, and reports which thesis claims have supporting, contradicting, or contextual historical evidence.

ThesisLens provides research context. It does not verify an investment thesis, forecast returns, or issue Buy/Sell/Hold recommendations.

## Features

- Annual revenue and net income observations from SEC CompanyFacts and 10-K filings.
- Financial snapshots, year-over-year growth, historical charts, and annual data tables.
- Rule-based thesis claim extraction and categorization.
- Supporting, contradicting, and neutral historical evidence for revenue and profitability claims.
- Thesis evidence coverage assessment with unsupported categories and research gaps.
- Company-specific SEC source links and filing references.

## Supported companies

| Company | Ticker |
| --- | --- |
| Microsoft | MSFT |
| Apple | AAPL |
| NVIDIA | NVDA |
| Amazon | AMZN |
| Alphabet | GOOGL |

## Technology stack

- Backend: Python, FastAPI, Pydantic, HTTPX, Uvicorn
- Frontend: React, TypeScript, Vite, Recharts, Lucide
- Tests: pytest, including mocked SEC HTTP requests
- Financial data: SEC CompanyFacts API

## Project structure

```text
backend/app/       FastAPI endpoints and SEC, analysis, thesis, and evidence logic
tests/             Backend unit and API tests
frontend/src/      React application and styles
frontend/public/   Frontend static assets
requirements.txt   Python backend and test dependencies
```

## Backend setup and run

Use Python 3.12. From the project root, create and activate a virtual environment, then install the pinned dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set the SEC user agent in the same PowerShell session before starting the API. Use an application label and a contact email you control:

```powershell
$env:SEC_USER_AGENT = "ThesisLens/0.1 contact your-email@example.com"
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`; FastAPI documentation is at `/docs`. SEC requests require `SEC_USER_AGENT` to identify the application and provide a contact email. The variable is not read from a `.env` file automatically.

## Frontend setup and run

In another terminal, install the frontend packages and start Vite:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` and `/health` requests to the backend at `http://127.0.0.1:8000`.

## Tests and frontend checks

Run backend tests from the project root:

```powershell
python -m pytest tests/ -v
```

Run frontend lint and production build from `frontend/`:

```powershell
npm run lint
npm run build
```

SEC HTTP requests are mocked in the backend tests; the tests do not require live SEC access.

## Known limitations

- Claim extraction and categorization use rules and keywords; they do not establish whether a claim is true.
- Historical evidence is currently limited to annual revenue and net income data. AI, cloud, competition, valuation, and other categories remain unsupported unless further verified data sources are added.
- Company-wide financial results do not establish performance for a specific business segment.
- Historical growth does not prove future performance or investment returns.
- The supported company universe is limited to the five US public companies listed above.
- SEC data availability and filing history can vary by company and period.

## Disclaimer

ThesisLens is for research and educational purposes only and is not financial advice. It does not provide personalized investment recommendations. Independently verify information against original SEC filings and consult a qualified financial professional where appropriate.
