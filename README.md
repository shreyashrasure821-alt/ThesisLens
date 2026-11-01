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

## Local Setup & Running the Application

### Prerequisites

- Python 3.12 installed on your computer
- Node.js and npm
- A contact email to include in the SEC request user agent

### Start the FastAPI backend

Open a PowerShell terminal at the project root. Create and activate the virtual environment, install the pinned backend and test dependencies, set the SEC user agent, then start the API. Replace the example Python executable path below with the path to your own Python 3.12 executable if it is installed elsewhere:

```powershell
Set-Location 'C:\Users\shrey\ThesisLens'
& "C:\Path\To\Python312\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SEC_USER_AGENT = "ThesisLens/0.1 Contact name@your-domain.example"
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The email shown is a placeholder. Replace it with a contact email you control. Set `SEC_USER_AGENT` in the same PowerShell session used to run the backend. The application does not load this setting from a `.env` file automatically.

### Start the React/Vite frontend

Open a **separate** PowerShell terminal and run:

```powershell
Set-Location 'C:\Users\shrey\ThesisLens\frontend'
npm install
npm run dev
```

Both the backend and frontend must be running for the dashboard and analysis workflows to work. Vite proxies `/api` and `/health` requests to the backend at `http://127.0.0.1:8000`.

### Local URLs

- Application: [http://localhost:5173/](http://localhost:5173/)
- Backend health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Swagger API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Dashboard & Analysis Walkthrough

1. **Select a company.** Choose Microsoft (MSFT), Apple (AAPL), NVIDIA (NVDA), Amazon (AMZN), or Alphabet (GOOGL). The dashboard and thesis evidence use the selected company.
2. **Review the financial snapshot.** The dashboard shows annual revenue and net income, along with historical year-over-year growth where comparable data is available.
3. **Submit a natural-language thesis.** Enter a thesis in the Thesis Lab and submit it for analysis.
4. **Review extracted claims and categories.** ThesisLens splits the text into claims and assigns categories using rule-based keyword classification.
5. **Read the evidence directions.** Revenue and profitability evidence can be marked supporting, contradicting, or neutral based on historical metrics. Neutral evidence gives context; historical results do not verify claims about future performance.
6. **Review unsupported claims and research gaps.** Categories without a supported evidence source are explicitly identified and may include suggestions for further research.
7. **Review the overall thesis assessment.** The assessment summarizes evidence coverage and research gaps, with limitations explaining what the available historical data can and cannot establish.

ThesisLens is an evidence-first research tool. It is not a stock prediction system and does not provide Buy/Sell/Hold recommendations.

## Screenshots

- **Dashboard screenshot:** _Placeholder — insert an actual dashboard screenshot after capturing one._
- **Thesis analysis screenshot:** _Placeholder — insert an actual thesis analysis screenshot after capturing one._

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
