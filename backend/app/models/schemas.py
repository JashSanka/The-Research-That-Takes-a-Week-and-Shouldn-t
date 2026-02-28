from pydantic import BaseModel, Field
from typing import List, Optional


# ─── Existing models (kept for backward compat) ───────────────────────────────

class ResearchQuery(BaseModel):
    query: str = Field(..., description="The user's research query")

class SubQuestion(BaseModel):
    id: str
    question: str

class SourceItem(BaseModel):
    title: str
    url: str
    published_date: Optional[str] = None
    snippet: str
    score: Optional[float] = None

class Insight(BaseModel):
    title: str
    description: str

class ResearchReport(BaseModel):
    executive_summary: str
    key_findings: List[Insight]
    risks_and_uncertainties: List[Insight]
    strategic_implications: List[Insight]
    sources: List[SourceItem]
    confidence_score: float
    freshness_index: float


# ─── Agent 1 — Junior Analyst ─────────────────────────────────────────────────

class SubQuestionPlan(BaseModel):
    sub_question_id: str          # "sq_1" … "sq_7"
    dimension: str                # "Market Size", "Regulation", etc.
    sub_question: str
    search_keywords: List[str]    # used to build Tavily query
    tavily_topic: str = "general" # "general" | "news" | "finance"

class ResearchPlan(BaseModel):
    original_query: str
    research_plan: List[SubQuestionPlan]


# ─── Agent 2 — Senior Analyst ─────────────────────────────────────────────────

class SourceEvaluation(BaseModel):
    url: str
    domain_type: str              # gov/edu/major_news/industry/blog/unknown
    credibility_score: float      # 0–10  (LLM-assigned)
    recency_score: float          # 0–10  (LLM-assigned)
    recency_points: int = 0       # 0–3   (rule-based engine)
    cross_ref_score: int = 0      # 0 or 2 (rule-based engine)
    key_fact_extracted: str

class Contradiction(BaseModel):
    claim_a: str
    source_a: str
    claim_b: str
    source_b: str
    stronger_signal: str

class SeniorAnalystOutput(BaseModel):
    sub_question_id: str
    sub_question: str
    sources: List[SourceItem]
    source_evaluations: List[SourceEvaluation]
    agreements: List[str]
    contradictions: List[Contradiction]
    verified_key_facts: List[str]


# ─── Agent 3 — Strategy Consultant ───────────────────────────────────────────

class KeyFinding(BaseModel):
    dimension: str
    finding: str
    supporting_sources: List[str]

class RiskUncertainty(BaseModel):
    risk: str
    origin: str

class StrategyConsultantOutput(BaseModel):
    original_query: str
    executive_summary: str
    key_findings: List[KeyFinding]
    strategic_implications: List[str]
    risks_and_uncertainties: List[RiskUncertainty]


# ─── Agent 4 — Risk Officer ───────────────────────────────────────────────────

class ConfidenceMetrics(BaseModel):
    average_source_credibility: float
    data_freshness_index: float       # 0–100
    agreement_factor: float           # 0–1
    total_sources_evaluated: int
    total_facts_extracted: int
    verified_facts_count: int
    contradiction_count: int

class RiskOfficerOutput(BaseModel):
    confidence_metrics: ConfidenceMetrics
    confidence_score: float           # 0–10
    confidence_label: str             # High / Moderate / Low
    report_reliability: str           # Ready for Decision / Review Recommended / Use with Caution
    confidence_reasoning: str
    audit_flags: List[str]


# ─── Final API Response ───────────────────────────────────────────────────────

class AgenticResearchReport(BaseModel):
    query: str
    research_plan: ResearchPlan
    senior_analysis: List[SeniorAnalystOutput]
    strategy_report: StrategyConsultantOutput
    risk_assessment: RiskOfficerOutput


# ─── Financial Intelligence Schemas ──────────────────────────────────────────

class FinancialRequest(BaseModel):
    company_name: str
    research_context: Optional[str] = None       # executive summary for VC scoring
    verified_facts: Optional[List[str]] = None
    audit_flags: Optional[List[str]] = None

class YearlyFinancial(BaseModel):
    year: str
    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    gross_margin: Optional[float] = None          # percentage
    eps: Optional[float] = None
    total_debt: Optional[float] = None
    total_equity: Optional[float] = None

class StockDataPoint(BaseModel):
    date: str
    close: float
    volume: Optional[int] = None

class KeyRatios(BaseModel):
    pe_ratio: Optional[float] = None
    market_cap_cr: Optional[float] = None         # Crores for Indian / Millions for US
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None    # %
    profit_margin: Optional[float] = None         # %

class VCDimensionScore(BaseModel):
    dimension: str
    score: int                                    # 1–10
    verdict: str                                  # Strong / Moderate / Weak / Unknown
    rationale: str

class FinancialIntelligence(BaseModel):
    # Public company fields (may be None for private/micro startups)
    ticker: Optional[str] = None
    company: str
    currency: str = "USD"
    yearly_financials: List[YearlyFinancial] = []
    stock_price_history: List[StockDataPoint] = []
    key_ratios: Optional[KeyRatios] = None
    # VC scoring (always present)
    vc_scorecard: List[VCDimensionScore] = []
    overall_vc_score: float = 0.0
    investment_verdict: str = "Insufficient Data"
    # Profile data
    tracxn_data: Optional["TracxnData"] = None
    web_intelligence: Optional["WebIntelligence"] = None
    is_private: bool = False        # True for unlisted/private companies


# ─── Tracxn Schemas ────────────────────────────────────────────────────────────

class TracxnMetric(BaseModel):
    label: str
    value: str

class TracxnCompetitor(BaseModel):
    name: str
    description: Optional[str] = None
    url: Optional[str] = None

class TracxnData(BaseModel):
    source_url: str
    about: str
    founded_year: Optional[str] = None
    headquarters: Optional[str] = None
    stage: Optional[str] = None
    total_funding: Optional[str] = None
    key_metrics: List[TracxnMetric] = []
    competitors: List[TracxnCompetitor] = []


# ─── Web Intelligence Schema (private / micro startups) ──────────────────────

class WebIntelligence(BaseModel):
    """Comprehensive startup profile fetched from public web sources."""
    company: str
    industry: Optional[str] = None
    business_model: Optional[str] = None
    annual_revenue: Optional[str] = None
    employee_count: Optional[str] = None
    valuation: Optional[str] = None
    founders: List[str] = []
    investors: List[str] = []
    products: List[str] = []
    recent_news: Optional[str] = None
    yearly_financials: List[YearlyFinancial] = []
    key_ratios: Optional[KeyRatios] = None
    company_profile: Optional[TracxnData] = None   # reuses TracxnData structure
