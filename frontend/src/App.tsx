
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, BookOpen,
  CheckCircle2, ChevronDown, CircleHelp, Clock3, ExternalLink,
  FileText, FlaskConical, LayoutDashboard, Menu, RefreshCw,
  Search, ShieldCheck, TrendingUp, X,
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import './App.css'

type FinancialYear = {
  fiscal_year: number
  revenue_usd_billions: number
  net_income_usd_billions: number
  revenue_growth_pct: number | null
  net_income_growth_pct: number | null
}

type AnalysisResponse = {
  company: string
  currency: string
  source_api: string
  methodology: string
  analysis: FinancialYear[]
}

type ThesisClaim = {
  claim_id: string
  claim_text: string
  categories: string[]
  evidence_required: string[]
  status: string
}

type EvidenceSource = {
  fiscal_year?: number | null
  filed_date?: string | null
  accession_number?: string | null
  url?: string | null
}

function evidenceSourceKey(evidenceId: string, source: EvidenceSource): string {
  return [
    evidenceId,
    source.fiscal_year ?? 'no-year',
    source.accession_number ?? 'no-accession',
    source.filed_date ?? 'no-filed-date',
    source.url ?? 'no-url',
  ].join('-')
}

type EvidenceItem = {
  evidence_id: string
  description: string
  direction: 'supporting' | 'contradicting' | 'neutral'
  metric: string
  fiscal_year: number
  value_pct: number | null
  change_percentage_points?: number | null
  signal: string
  interpretation: string
  sources: EvidenceSource[]
}

type EvidenceClaim = {
  claim_id: string
  claim_text: string
  categories: string[]
  evidence_status: string
  evidence: EvidenceItem[]
  unsupported_categories: string[]
}

type ThesisAssessment = {
  overall_coverage:
    | 'full_historical_coverage'
    | 'partial_coverage'
    | 'insufficient_evidence'
  total_claims: number
  claims_with_historical_context: number
  partially_covered_claims: number
  claims_with_insufficient_evidence: number
  unsupported_categories: string[]
  research_gaps: { category: string; gap: string }[]
  limitations: string[]
  assessment_summary: string
}

type ThesisEvidenceResponse = {
  thesis_analysis: {
    thesis: string
    analysis_method: string
    claim_count: number
    claims: ThesisClaim[]
    limitations: string
  }
  evidence_report: {
    company: string
    evidence_method: string
    periods_available: number[]
    supported_categories: string[]
    unavailable_categories: string[]
    claims: EvidenceClaim[]
    limitations: string[]
  }
  thesis_assessment: ThesisAssessment
}

function isThesisAssessment(value: unknown): value is ThesisAssessment {
  if (typeof value !== 'object' || value === null) return false

  const assessment = value as Record<string, unknown>
  const validCoverage = [
    'full_historical_coverage',
    'partial_coverage',
    'insufficient_evidence',
  ].includes(String(assessment.overall_coverage))
  const validCount = (count: unknown) =>
    typeof count === 'number' && Number.isInteger(count) && count >= 0
  const countsMatchTotal =
    validCount(assessment.total_claims) &&
    validCount(assessment.claims_with_historical_context) &&
    validCount(assessment.partially_covered_claims) &&
    validCount(assessment.claims_with_insufficient_evidence) &&
    Number(assessment.claims_with_historical_context) +
      Number(assessment.partially_covered_claims) +
      Number(assessment.claims_with_insufficient_evidence) ===
      Number(assessment.total_claims)

  return validCoverage &&
    countsMatchTotal &&
    Array.isArray(assessment.unsupported_categories) &&
    assessment.unsupported_categories.every((item) => typeof item === 'string') &&
    Array.isArray(assessment.research_gaps) &&
    assessment.research_gaps.every((item) =>
      typeof item === 'object' && item !== null &&
      typeof (item as Record<string, unknown>).category === 'string' &&
      typeof (item as Record<string, unknown>).gap === 'string',
    ) &&
    Array.isArray(assessment.limitations) &&
    assessment.limitations.every((item) => typeof item === 'string') &&
    typeof assessment.assessment_summary === 'string'
}

function formatCoverageStatus(status: ThesisAssessment['overall_coverage']): string {
  const labels: Record<ThesisAssessment['overall_coverage'], string> = {
    full_historical_coverage: 'Full Historical Coverage',
    partial_coverage: 'Partial Coverage',
    insufficient_evidence: 'Insufficient Evidence',
  }

  return labels[status]
}

const COMPANY_OPTIONS = [
  { ticker: 'MSFT', name: 'Microsoft', cik: '0000789019' },
  { ticker: 'AAPL', name: 'Apple', cik: '0000320193' },
  { ticker: 'NVDA', name: 'NVIDIA', cik: '0001045810' },
  { ticker: 'AMZN', name: 'Amazon', cik: '0001018724' },
  { ticker: 'GOOGL', name: 'Alphabet', cik: '0001652044' },
] as const

type CompanyTicker = (typeof COMPANY_OPTIONS)[number]['ticker']

function money(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 1,
  }).format(value) + 'B'
}

function percent(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function humanize(value: string): string {
  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function formatEvidenceStatus(status: string): string {
  const labels: Record<string, string> = {
    partial_coverage: 'Partial evidence coverage',
    historical_context_available: 'Historical context available',
    insufficient_evidence: 'Insufficient evidence',
  }

  return labels[status] ?? humanize(status)
}

function formatEvidenceValue(item: EvidenceItem): string {
  if (item.value_pct == null) return 'Not available'

  if (item.metric === 'net_income_margin') {
    return `${item.value_pct.toFixed(2)}%`
  }

  return `${item.value_pct > 0 ? '+' : ''}${item.value_pct.toFixed(2)}%`
}

function evidenceStatusDescription(status: string): string {
  switch (status) {
    case 'partial_coverage':
      return 'Some aspects have historical financial evidence, but other categories remain unsupported. This does not mean the complete claim is proven.'

    case 'historical_context_available':
      return 'Historical financial indicators are available. They provide context, not proof of the investment thesis.'

    default:
      return 'The current dataset does not contain financial evidence relevant to this claim.'
  }
}

function App() {
  const [selectedTicker, setSelectedTicker] = useState<CompanyTicker>('MSFT')
  const [data, setData] = useState<AnalysisResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [thesis, setThesis] = useState('')
  const [thesisSubmitting, setThesisSubmitting] = useState(false)
  const [thesisError, setThesisError] = useState('')
  const [thesisResult, setThesisResult] =
    useState<ThesisEvidenceResponse | null>(null)
  const [mobileNav, setMobileNav] = useState(false)
  const [metric, setMetric] = useState<'revenue' | 'income'>('revenue')
  const [period, setPeriod] = useState('5Y')
  const financialRequestId = useRef(0)
  const selectedCompany = COMPANY_OPTIONS.find(
    (company) => company.ticker === selectedTicker,
  )!
  const secUrl = `https://data.sec.gov/api/xbrl/companyfacts/CIK${selectedCompany.cik}.json`
  const secFilingsUrl = `https://www.sec.gov/edgar/browse/?CIK=${Number(selectedCompany.cik)}&owner=exclude`

  const loadData = useCallback(async () => {
    const requestId = ++financialRequestId.current
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`/api/companies/${selectedTicker}/analysis`)
      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`)
      }
      const result = (await response.json()) as AnalysisResponse
      if (!Array.isArray(result.analysis) || result.analysis.length === 0) {
        throw new Error('The API returned no annual financial observations.')
      }
      if (requestId !== financialRequestId.current) return
      setData(result)
    } catch (err) {
      if (requestId !== financialRequestId.current) return
      setError(
        err instanceof Error
          ? err.message
          : 'Could not connect to the ThesisLens API.',
      )
    } finally {
      if (requestId === financialRequestId.current) setLoading(false)
    }
  }, [selectedTicker])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadData()
    }, 0)
    return () => {
      window.clearTimeout(timer)
      financialRequestId.current += 1
    }
  }, [loadData])

  const years = useMemo(
    () => [...(data?.analysis ?? [])].sort((a, b) => a.fiscal_year - b.fiscal_year),
    [data],
  )

  const latest = data?.analysis[0]

  const chartData = useMemo(() => {
    const selected = period === '3Y' ? years.slice(-3) : years
    return selected.map((row) => ({
      year: `FY${row.fiscal_year}`,
      Revenue: row.revenue_usd_billions,
      'Net income': row.net_income_usd_billions,
    }))
  }, [years, period])

  const visibleMetrics = metric === 'revenue' ? 'Revenue' : 'Net income'
  const currentGrowth =
    metric === 'revenue'
      ? latest?.revenue_growth_pct
      : latest?.net_income_growth_pct

  const filteredYears = years.filter((row) =>
    String(row.fiscal_year).includes(query.trim()),
  )
  const thesisAssessment = thesisResult &&
    isThesisAssessment(thesisResult.thesis_assessment)
    ? thesisResult.thesis_assessment
    : null

  async function handleThesisSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const submittedThesis = thesis.trim()

    if (submittedThesis.length < 10) {
      setThesisError('Please enter at least 10 characters.')
      return
    }

    if (submittedThesis.length > 4000) {
      setThesisError('Thesis cannot exceed 4000 characters.')
      return
    }

    setThesisSubmitting(true)
    setThesisError('')
    setThesisResult(null)

    try {
      const response = await fetch('/api/thesis/evidence', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          thesis: submittedThesis,
          ticker: selectedTicker,
        }),
      })

      const payload = await response.json().catch(() => null) as
        | ThesisEvidenceResponse
        | { detail?: string }
        | null

      if (!response.ok) {
        const detail =
          payload &&
            'detail' in payload &&
            typeof payload.detail === 'string'
            ? payload.detail
            : `Backend returned HTTP ${response.status}`

        throw new Error(detail)
      }

      if (
        !payload ||
        !('thesis_analysis' in payload) ||
        !('evidence_report' in payload)
      ) {
        throw new Error('Backend returned an invalid evidence report.')
      }

      setThesisResult(payload as ThesisEvidenceResponse)

    } catch (err) {
      setThesisError(
        err instanceof Error
          ? err.message
          : 'Could not analyze the investment thesis.',
      )
    } finally {
      setThesisSubmitting(false)
    }
  }

  return (
    <div className="app-shell">
      {mobileNav && (
        <button
          className="mobile-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}

      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Activity size={22} /></div>
          <div>
            <div className="brand-name">ThesisLens</div>
            <div className="brand-caption">RESEARCH TERMINAL</div>
          </div>
          <button className="icon-button mobile-close" onClick={() => setMobileNav(false)} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav">
          <a className="nav-link active" href="#overview" onClick={() => setMobileNav(false)}>
            <LayoutDashboard size={18} /> Overview
          </a>
          <a className="nav-link" href="#financials" onClick={() => setMobileNav(false)}>
            <BarChart3 size={18} /> Financial evidence
          </a>
          <a className="nav-link" href="#thesis" onClick={() => setMobileNav(false)}>
            <FlaskConical size={18} /> Thesis lab <span className="nav-tag">BETA</span>
          </a>
          <a className="nav-link" href="#sources" onClick={() => setMobileNav(false)}>
            <BookOpen size={18} /> Source library
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="data-status">
            <span className="status-dot" />
            <div>
              <strong>Evidence pipeline</strong>
              <span>SEC CompanyFacts API</span>
            </div>
          </div>
          <div className="sidebar-footer">
            <ShieldCheck size={15} /> Evidence before conviction
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">
            <button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation">
              <Menu size={20} />
            </button>
            <span>Workspace</span><span className="crumb-divider">/</span><strong>Company research</strong>
          </div>
          <div className="topbar-right">
            <span className="live-indicator"><span className="status-dot" /> API connected</span>
            <button className="icon-button refresh-button" onClick={() => void loadData()} disabled={loading} aria-label="Refresh financial data">
              <RefreshCw size={17} className={loading ? 'spin' : ''} />
            </button>
            <div className="avatar">TL</div>
          </div>
        </header>

        <div className="page-content">
          <section className="page-heading" id="overview">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> INVESTMENT RESEARCH / US EQUITIES</div>
              <h1>Challenge your thesis.<br /><span>Follow the evidence.</span></h1>
              <p className="page-description">
                Research a company’s fundamentals before deciding what you believe.
                Start with reported numbers, then question your assumptions.
              </p>
            </div>
            <div className="heading-badge"><ShieldCheck size={16} /> Evidence-first analysis</div>
          </section>

          <section className="company-card">
            <div className="company-identity">
              <div className="company-logo">{selectedCompany.name[0]}</div>
              <div>
                <div className="company-overline">US EQUITIES &middot; {selectedTicker}</div>
                <h2>{data?.company ?? selectedCompany.name}</h2>
                <div className="company-subtitle">{selectedCompany.name} fundamentals</div>
              </div>
            </div>
            <div className="company-card-actions">
              <label className="company-picker">
                <span>Company</span>
                <span className="select-wrap">
                  <select
                    aria-label="Select company"
                    value={selectedTicker}
                    disabled={thesisSubmitting}
                    onChange={(event) => {
                      const ticker = event.target.value as CompanyTicker
                      financialRequestId.current += 1
                      setSelectedTicker(ticker)
                      setData(null)
                      setThesisResult(null)
                      setThesisError('')
                      setError('')
                    }}
                  >
                    {COMPANY_OPTIONS.map((company) => (
                      <option key={company.ticker} value={company.ticker}>
                        {company.name} ({company.ticker})
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={14} />
                </span>
              </label>
              <span className="data-pill">
                {loading ? <RefreshCw size={14} className="spin" /> : <span className="status-dot" />}
                {loading ? `Loading ${selectedTicker} SEC data` : 'SEC fundamentals'}
              </span>
              <button className="outline-button" onClick={() => void loadData()} disabled={loading}>
                <RefreshCw size={15} /> Refresh data
              </button>
            </div>
          </section>
          {error && (
            <div className="error-banner" role="alert">
              <CircleHelp size={20} />
              <div><strong>Unable to load {selectedCompany.name} data</strong><p>{error}. Confirm that the FastAPI backend is running, then retry.</p></div>
              <button className="outline-button" onClick={() => void loadData()}>Retry</button>
            </div>
          )}

          <section className="section-block">
            <div className="section-heading">
              <div><span className="section-kicker">01 / FUNDAMENTALS</span><h2>Financial snapshot</h2></div>
              <span className="subtle-meta"><Clock3 size={14} /> Annual reported data</span>
            </div>

            <div className="metric-grid">
              <article className="metric-card">
                <div className="metric-top"><span>Annual revenue</span><span className="metric-icon violet"><BarChart3 size={17} /></span></div>
                <div className="metric-value">{loading && !latest ? 'Loading…' : latest ? money(latest.revenue_usd_billions) : '—'}</div>
                <div className="metric-foot">
                  <span className={`growth-chip ${(latest?.revenue_growth_pct ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                    {(latest?.revenue_growth_pct ?? 0) >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                    {percent(latest?.revenue_growth_pct ?? null)}
                  </span>
                  <span>year over year</span>
                </div>
                <div className="metric-note">{latest ? `Fiscal year ${latest.fiscal_year}` : 'Waiting for API'}</div>
              </article>

              <article className="metric-card">
                <div className="metric-top"><span>Net income</span><span className="metric-icon green"><TrendingUp size={17} /></span></div>
                <div className="metric-value">{loading && !latest ? 'Loading…' : latest ? money(latest.net_income_usd_billions) : '—'}</div>
                <div className="metric-foot">
                  <span className={`growth-chip ${(latest?.net_income_growth_pct ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                    {(latest?.net_income_growth_pct ?? 0) >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                    {percent(latest?.net_income_growth_pct ?? null)}
                  </span>
                  <span>year over year</span>
                </div>
                <div className="metric-note">{latest ? `Fiscal year ${latest.fiscal_year}` : 'Waiting for API'}</div>
              </article>

              <article className="metric-card">
                <div className="metric-top"><span>Revenue growth</span><span className="metric-icon blue"><Activity size={17} /></span></div>
                <div className="metric-value">{percent(latest?.revenue_growth_pct ?? null)}</div>
                <div className="metric-foot"><span className="metric-label">Latest reported period</span></div>
                <div className="metric-note">Compared with previous fiscal year</div>
              </article>

              <article className="metric-card">
                <div className="metric-top"><span>Net income growth</span><span className="metric-icon amber"><TrendingUp size={17} /></span></div>
                <div className="metric-value">{percent(latest?.net_income_growth_pct ?? null)}</div>
                <div className="metric-foot"><span className="metric-label">Latest reported period</span></div>
                <div className="metric-note">Earnings growth is not valuation</div>
              </article>
            </div>
          </section>

          <section className="section-block" id="financials">
            <div className="section-heading">
              <div><span className="section-kicker">02 / HISTORICAL TRENDS</span><h2>Financial performance</h2></div>
              <div className="chart-controls">
                <div className="segmented-control">
                  <button className={metric === 'revenue' ? 'selected' : ''} onClick={() => setMetric('revenue')}>Revenue</button>
                  <button className={metric === 'income' ? 'selected' : ''} onClick={() => setMetric('income')}>Net income</button>
                </div>
                <div className="select-wrap">
                  <select value={period} onChange={(event) => setPeriod(event.target.value)} aria-label="Chart time period">
                    <option value="5Y">5 years</option><option value="3Y">3 years</option>
                  </select><ChevronDown size={14} />
                </div>
              </div>
            </div>

            <div className="chart-card">
              <div className="chart-summary">
                <div><span className="chart-value">{latest ? money(metric === 'revenue' ? latest.revenue_usd_billions : latest.net_income_usd_billions) : '—'}</span><span className="chart-caption">Latest annual observation</span></div>
                <div className={`chart-growth ${(currentGrowth ?? 0) >= 0 ? 'positive-text' : 'negative-text'}`}>{percent(currentGrowth)} <span>YoY</span></div>
              </div>
              {loading && !data ? (
                <div className="chart-placeholder"><RefreshCw className="spin" size={22} /> Loading reported financials…</div>
              ) : (
                <div className="chart-canvas">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 12, right: 10, left: -14, bottom: 0 }}>
                      <defs>
                        <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.28} />
                          <stop offset="95%" stopColor="#a78bfa" stopOpacity={0.01} />
                        </linearGradient>
                        <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#34d399" stopOpacity={0.23} />
                          <stop offset="95%" stopColor="#34d399" stopOpacity={0.01} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#252a36" strokeDasharray="3 5" vertical={false} />
                      <XAxis dataKey="year" tick={{ fill: '#8991a4', fontSize: 12 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: '#8991a4', fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(value: number) => `$${value}B`} />
                      <Tooltip
                        contentStyle={{ background: '#141923', border: '1px solid #303748', borderRadius: 10, color: '#f4f5fb' }}
                        formatter={(value) => [`$${Number(value).toFixed(2)}B`, visibleMetrics]}
                      />
                      <Legend wrapperStyle={{ color: '#a7adbd', fontSize: 12 }} />
                      {metric === 'revenue' ? (
                        <Area type="monotone" dataKey="Revenue" stroke="#a78bfa" strokeWidth={2.5} fill="url(#revenueGradient)" activeDot={{ r: 5 }} />
                      ) : (
                        <Area type="monotone" dataKey="Net income" stroke="#34d399" strokeWidth={2.5} fill="url(#incomeGradient)" activeDot={{ r: 5 }} />
                      )}
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
              <div className="chart-footnote">Values in USD billions · Fiscal-year observations · Source: SEC CompanyFacts API</div>
            </div>
          </section>

          <section className="section-block" id="thesis">
            <div className="section-heading">
              <div>
                <span className="section-kicker">03 / THESIS LAB</span>
                <h2>Put your thesis to the test</h2>
              </div>
              <span className="beta-pill">CONNECTED / BETA</span>
            </div>

            <div className="thesis-card">

              <div className="thesis-intro">
                <div className="thesis-icon">
                  <FlaskConical size={21} />
                </div>
                <div>
                  <h3>What do you believe about {selectedCompany.name}?</h3>
                  <p>
                    Enter your investment thesis. ThesisLens will break it into
                    claims and investigate which claims have supporting historical
                    financial evidence.
                  </p>
                </div>
              </div>

              <form onSubmit={handleThesisSubmit}>
                <label htmlFor="thesis-input">
                  YOUR INVESTMENT THESIS
                </label>

                <textarea
                  id="thesis-input"
                  value={thesis}
                  onChange={(event) => setThesis(event.target.value)}
                  placeholder={`Example: ${selectedCompany.name} can sustain revenue growth through durable customer demand...`}
                  rows={4}
                  maxLength={4000}
                  disabled={thesisSubmitting}
                />

                <div className="thesis-form-bottom">
                  <span>
                    {thesis.length} / 4000 characters
                    <span className="bullet"> • </span>
                    Processed by ThesisLens backend
                  </span>

                  <button
                    className="primary-button"
                    type="submit"
                    disabled={
                      !thesis.trim() ||
                      thesis.trim().length < 10 ||
                      thesisSubmitting
                    }
                  >
                    {thesisSubmitting ? (
                      <>
                        <RefreshCw size={15} className="spin" />
                        Analyzing thesis...
                      </>
                    ) : (
                      <>
                        Analyze thesis
                        <ArrowUpRight size={16} />
                      </>
                    )}
                  </button>
                </div>
              </form>

              {thesisError && (
                <div className="evidence-note thesis-error" role="alert">
                  <CircleHelp size={17} />
                  <div>
                    <strong>Analysis failed</strong>
                    <p>{thesisError}</p>
                  </div>
                </div>
              )}

              {thesisSubmitting && (
                <div className="evidence-note">
                  <RefreshCw size={17} className="spin" />
                  <div>
                    <strong>Investigating your thesis</strong>
                    <p>
                      Extracting claims and retrieving historical SEC financial
                      evidence for {selectedCompany.name} ({selectedTicker}).
                    </p>
                  </div>
                </div>
              )}

              {!thesisSubmitting && !thesisError && !thesisResult && (
                <div className="evidence-note">
                  <CircleHelp size={17} />
                  <div>
                    <strong>Evidence-first analysis</strong>
                    <p>
                      Claims are classified and matched against available
                      historical financial data. Unsupported claims remain
                      explicitly identified. No investment verdict is generated.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {thesisResult && (
              <div className="thesis-results" id="thesis-results">

                <div className="results-header">
                  <div>
                    <span className="section-kicker">ANALYSIS OUTPUT</span>
                    <h3>Thesis evidence report</h3>
                    <p>
                      {thesisResult.evidence_report.company}
                      {' · '}
                      {thesisResult.thesis_analysis.claim_count} claims extracted
                    </p>
                  </div>
                  <span className="data-pill">
                    <CheckCircle2 size={14} />
                    Analysis complete
                  </span>
                </div>

                <div className="results-summary">
                  <div>
                    <span>Fiscal years evaluated</span>
                    <strong>
                      {thesisResult.evidence_report.periods_available.join(' · ')}
                    </strong>
                  </div>
                  <div>
                    <span>Evidence-supported categories</span>
                    <strong>
                      {thesisResult.evidence_report.supported_categories
                        .map(humanize)
                        .join(', ')}
                    </strong>
                  </div>
                  <div>
                    <span>Unavailable categories</span>
                    <strong>
                      {thesisResult.evidence_report.unavailable_categories.length
                        ? thesisResult.evidence_report.unavailable_categories
                          .map(humanize)
                          .join(', ')
                        : 'None'}
                    </strong>
                  </div>
                </div>

                {thesisAssessment ? (
                  <section className="thesis-assessment" aria-labelledby="assessment-title">
                    <div className="assessment-header">
                      <div>
                        <span className="section-kicker">ASSESSMENT</span>
                        <h3 id="assessment-title">Overall Thesis Assessment</h3>
                      </div>
                      <span className={`assessment-status status-${thesisAssessment.overall_coverage}`}>
                        {formatCoverageStatus(thesisAssessment.overall_coverage)}
                      </span>
                    </div>

                    <div className="assessment-coverage-label">Overall Evidence Coverage</div>

                    <div className="assessment-stat-grid" aria-label="Claim statistics">
                      <div><span>Total Claims</span><strong>{thesisAssessment.total_claims}</strong></div>
                      <div><span>Claims with Historical Context</span><strong>{thesisAssessment.claims_with_historical_context}</strong></div>
                      <div><span>Partially Covered Claims</span><strong>{thesisAssessment.partially_covered_claims}</strong></div>
                      <div><span>Claims with Insufficient Evidence</span><strong>{thesisAssessment.claims_with_insufficient_evidence}</strong></div>
                    </div>

                    <div className="assessment-summary-block">
                      <h4>Assessment Summary</h4>
                      <p>{thesisAssessment.assessment_summary}</p>
                    </div>

                    <div className="assessment-research">
                      <div>
                        <h4>Research Gaps</h4>
                        {thesisAssessment.unsupported_categories.length > 0 ? (
                          <div className="category-list">
                            {thesisAssessment.unsupported_categories.map((category) => (
                              <span className="category-tag" key={category}>{humanize(category)}</span>
                            ))}
                          </div>
                        ) : (
                          <p className="assessment-empty">No unsupported categories were reported.</p>
                        )}
                      </div>
                      {thesisAssessment.research_gaps.length > 0 ? (
                        <ul className="assessment-gap-list">
                          {thesisAssessment.research_gaps.map((gap) => (
                            <li key={gap.category}>
                              <strong>{humanize(gap.category)}</strong>
                              <span>{gap.gap}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="assessment-empty">No category-specific research gaps were returned.</p>
                      )}
                    </div>

                    <div className="results-limitations assessment-limitations">
                      <h4>Methodology Limitations</h4>
                      <ul>
                        {thesisAssessment.limitations.map((item, index) => (
                          <li key={`${index}-${item}`}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  </section>
                ) : (
                  <div className="assessment-fallback" role="status">
                    Overall thesis assessment is unavailable because the backend did not return a valid assessment.
                  </div>
                )}

                <div className="claim-list">
                  {thesisResult.evidence_report.claims.map((claim) => {
                    const extractedClaim =
                      thesisResult.thesis_analysis.claims.find(
                        (item) => item.claim_id === claim.claim_id,
                      )

                    return (
                      <article className="claim-result" key={claim.claim_id}>

                        <div className="claim-top">
                          <div>
                            <span className="claim-id">
                              CLAIM {claim.claim_id}
                            </span>
                            <h4>{claim.claim_text}</h4>
                          </div>

                          <span
                            className={`status-pill status-${claim.evidence_status}`}
                          >
                            {formatEvidenceStatus(claim.evidence_status)}
                          </span>
                        </div>

                        <div className="category-list">
                          {claim.categories.map((category) => (
                            <span className="category-tag" key={category}>
                              {humanize(category)}
                            </span>
                          ))}
                        </div>

                        <p className="claim-description">
                          {evidenceStatusDescription(claim.evidence_status)}
                        </p>

                        {claim.evidence.length > 0 ? (
                          <div className="evidence-items">
                            <h5>Historical financial evidence</h5>

                            {claim.evidence.map((item) => (
                              <div className="evidence-item" key={item.evidence_id}>
                                <div className="evidence-item-header">
                                  <div>
                                    <span className="evidence-id">
                                      {item.evidence_id}
                                    </span>
                                    <span className={`evidence-direction direction-${item.direction}`}>
                                      {humanize(item.direction)} evidence
                                    </span>
                                    <h6>{humanize(item.metric)}</h6>
                                  </div>

                                  <strong className="evidence-value">
                                    {formatEvidenceValue(item)}
                                  </strong>
                                </div>

                                <div className="evidence-meta">
                                  FY{item.fiscal_year}
                                  {' · '}
                                  {humanize(item.signal)}
                                  {item.change_percentage_points != null && (
                                    <>
                                      {' · '}
                                      {item.change_percentage_points > 0 ? '+' : ''}
                                      {item.change_percentage_points.toFixed(2)}
                                      {' percentage points'}
                                    </>
                                  )}
                                </div>

                                <p><strong>{item.description}</strong> {item.interpretation}</p>

                                <div className="evidence-sources">
                                  <span>Source filings:</span>

                                  {item.sources.length > 0 ? item.sources.map((source) => source.url ? (
                                    <a
                                      key={evidenceSourceKey(item.evidence_id, source)}
                                      href={source.url}
                                      target="_blank"
                                      rel="noreferrer"
                                    >
                                      {source.fiscal_year ? `FY${source.fiscal_year}` : 'SEC'}
                                      {' · '}
                                      SEC filing
                                      <ExternalLink size={12} />
                                    </a>
                                  ) : (
                                    <span key={evidenceSourceKey(item.evidence_id, source)}>
                                      {source.fiscal_year ? `FY${source.fiscal_year}` : 'SEC'} source URL unavailable
                                    </span>
                                  )) : (
                                    <span>No SEC source URL is available.</span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="no-evidence">
                            No matching historical financial evidence is available
                            in the current dataset.
                          </div>
                        )}

                        {claim.unsupported_categories.length > 0 && (
                          <div className="coverage-warning">
                            <strong>Research gaps:</strong>
                            {' '}
                            {claim.unsupported_categories
                              .map(humanize)
                              .join(', ')}
                            {' '}
                            require additional verified sources.
                          </div>
                        )}

                        {extractedClaim && (
                          <details className="claim-requirements">
                            <summary>Evidence requirements identified</summary>
                            <ul>
                              {extractedClaim.evidence_required.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </details>
                        )}

                      </article>
                    )
                  })}
                </div>

                <div className="evidence-note results-disclaimer">
                  <ShieldCheck size={17} />
                  <div>
                    <strong>Evidence coverage is not claim verification</strong>
                    <p>
                      Positive historical trends do not prove future performance
                      or establish that an investment thesis is correct.
                      Unsupported claims require further investigation.
                    </p>
                  </div>
                </div>

                <div className="results-limitations">
                  <h4>Methodology limitations</h4>
                  <ul>
                    {thesisResult.evidence_report.limitations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>

              </div>
            )}
          </section>

          <section className="section-block" id="sources">
            <div className="section-heading">
              <div><span className="section-kicker">04 / PROVENANCE</span><h2>Sources & methodology</h2></div>
              <span className="verified-label"><CheckCircle2 size={15} /> Primary-source endpoint</span>
            </div>
            <div className="sources-grid">
              <article className="source-card">
                <div className="source-icon"><FileText size={19} /></div>
                <div className="source-body">
                  <span className="source-type">PRIMARY DATA</span>
                  <h3>SEC CompanyFacts</h3>
                  <p>Company-reported XBRL facts used by the backend to extract annual revenue and net income observations.</p>
                  <a href={secUrl} target="_blank" rel="noreferrer">Open SEC data <ExternalLink size={13} /></a>
                </div>
              </article>
              <article className="source-card">
                <div className="source-icon"><BookOpen size={19} /></div>
                <div className="source-body">
                  <span className="source-type">FILING REFERENCE</span>
                  <h3>SEC company filings</h3>
                  <p>Review original filings and compare fiscal-year figures before relying on any derived growth metric.</p>
                  <a href={secFilingsUrl} target="_blank" rel="noreferrer">Browse filings <ExternalLink size={13} /></a>
                </div>
              </article>
            </div>

            <div className="methodology-card">
              <div className="methodology-title"><ShieldCheck size={18} /><strong>How to interpret this data</strong></div>
              <p>{data?.methodology ?? 'Annual SEC observations are used to calculate year-over-year growth.'}</p>
              <ul>
                <li>Growth is calculated from the previous available fiscal-year observation.</li>
                <li>Reported revenue and net income do not establish fair value or predict future returns.</li>
                <li>Confirm each period against its original 10-K filing; the backend methodology text and filing attribution still need review.</li>
              </ul>
              {data && (
                <div className="source-endpoint">
                  <span>API source</span>
                  <a href={data.source_api} target="_blank" rel="noreferrer">CompanyFacts JSON <ExternalLink size={13} /></a>
                </div>
              )}
            </div>
          </section>

          <section className="section-block table-section">
            <div className="section-heading">
              <div><span className="section-kicker">DATA EXPLORER</span><h2>Annual observations</h2></div>
              <label className="table-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter fiscal year…" /></label>
            </div>
            <div className="table-card">
              <div className="table-scroll">
                <table>
                  <thead><tr><th>Fiscal year</th><th>Revenue</th><th>Revenue growth</th><th>Net income</th><th>Income growth</th></tr></thead>
                  <tbody>
                    {filteredYears.slice().reverse().map((row) => (
                      <tr key={row.fiscal_year}>
                        <td><strong>FY {row.fiscal_year}</strong></td>
                        <td>{money(row.revenue_usd_billions)}</td>
                        <td className={(row.revenue_growth_pct ?? 0) >= 0 ? 'positive-text' : 'negative-text'}>{percent(row.revenue_growth_pct)}</td>
                        <td>{money(row.net_income_usd_billions)}</td>
                        <td className={(row.net_income_growth_pct ?? 0) >= 0 ? 'positive-text' : 'negative-text'}>{percent(row.net_income_growth_pct)}</td>
                      </tr>
                    ))}
                    {!loading && filteredYears.length === 0 && <tr><td colSpan={5} className="empty-row">No fiscal years match your filter.</td></tr>}
                  </tbody>
                </table>
              </div>
              <div className="table-footer">{filteredYears.length} annual observations <span>·</span> USD billions unless noted</div>
            </div>
          </section>

          <footer className="page-footer">
            <div className="footer-brand"><div className="brand-mark small"><Activity size={16} /></div><strong>ThesisLens</strong><span>v0.1 prototype</span></div>
            <p>Research support, not financial advice. Verify source filings independently.</p>
            <a href={secFilingsUrl} target="_blank" rel="noreferrer">SEC filings <ExternalLink size={12} /></a>
          </footer>
        </div>
      </main>
    </div>
  )
}

export default App
