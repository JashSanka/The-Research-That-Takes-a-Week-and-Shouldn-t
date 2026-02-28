"""
Financial route — handles both public (listed) and private (unlisted/micro) companies.

PATH A (Public company):
  ticker found → yfinance + Tracxn + VC Analyst

PATH B (Private / micro startup):
  no ticker → Web Intelligence (Tavily web search) + Tracxn + VC Analyst
"""
import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import FinancialRequest, FinancialIntelligence
from app.services.financial_data import resolve_ticker, fetch_financials
from app.services.tracxn_scraper import fetch_tracxn_data
from app.services.web_intelligence import fetch_web_intelligence
from app.agents import vc_analyst

router = APIRouter()


@router.post("/company-data", response_model=FinancialIntelligence)
async def get_company_financial_data(body: FinancialRequest):
    """
    Universal company intelligence endpoint.
    - Public companies: fetches yfinance + Tracxn + VC scoring
    - Private/micro startups: fetches web intelligence + Tracxn + VC scoring
    """
    ticker_symbol = resolve_ticker(body.company_name)
    is_private = ticker_symbol is None

    # ── PATH A: Public company ────────────────────────────────────────────────
    if not is_private:
        return await _handle_public_company(body, ticker_symbol)

    # ── PATH B: Private / micro startup ──────────────────────────────────────
    return await _handle_private_company(body)


async def _handle_public_company(
    body: FinancialRequest, ticker_symbol: str
) -> FinancialIntelligence:
    """Handles listed companies: yfinance + Tracxn + VC scoring."""
    loop = asyncio.get_event_loop()

    yf_task = loop.run_in_executor(None, fetch_financials, ticker_symbol)
    tracxn_task = fetch_tracxn_data(body.company_name)

    yf_data, tracxn_data = await asyncio.gather(
        yf_task, tracxn_task, return_exceptions=True
    )

    if isinstance(yf_data, Exception):
        raise HTTPException(status_code=502, detail=f"yfinance error: {yf_data}")

    if isinstance(tracxn_data, Exception):
        tracxn_data = None

    # Enrich VC scoring with Tracxn facts
    tracxn_facts = _extract_tracxn_facts(tracxn_data)
    all_facts = (body.verified_facts or []) + tracxn_facts

    fin_dicts = [yf.model_dump() for yf in yf_data["yearly_financials"]]
    scorecard, overall_score, verdict = await vc_analyst.score_company(
        company=yf_data["company"],
        key_ratios=yf_data["key_ratios"].model_dump(),
        yearly_financials=fin_dicts,
        executive_summary=body.research_context or "",
        verified_facts=all_facts[:12],
        audit_flags=body.audit_flags or [],
    )

    return FinancialIntelligence(
        ticker=ticker_symbol,
        company=yf_data["company"],
        currency=yf_data["currency"],
        yearly_financials=yf_data["yearly_financials"],
        stock_price_history=yf_data["stock_price_history"],
        key_ratios=yf_data["key_ratios"],
        vc_scorecard=scorecard,
        overall_vc_score=overall_score,
        investment_verdict=verdict,
        tracxn_data=tracxn_data if not isinstance(tracxn_data, Exception) else None,
        is_private=False,
    )


async def _handle_private_company(body: FinancialRequest) -> FinancialIntelligence:
    """Handles private/micro startups: web intelligence + Tracxn + VC scoring."""
    print(f"[Financial] {body.company_name} — private company path (no yfinance ticker)")

    # Run both data sources concurrently
    web_task = fetch_web_intelligence(body.company_name)
    tracxn_task = fetch_tracxn_data(body.company_name)

    web_intel, tracxn_data = await asyncio.gather(
        web_task, tracxn_task, return_exceptions=True
    )

    if isinstance(web_intel, Exception):
        web_intel = None
    if isinstance(tracxn_data, Exception):
        tracxn_data = None

    # Aggregate facts for VC scoring from all sources
    facts: list[str] = list(body.verified_facts or [])
    if web_intel:
        if web_intel.company_profile and web_intel.company_profile.about:
            facts.append(web_intel.company_profile.about)
        if web_intel.annual_revenue:
            facts.append(f"Annual Revenue: {web_intel.annual_revenue}")
        if web_intel.employee_count:
            facts.append(f"Employees: {web_intel.employee_count}")
        if web_intel.valuation:
            facts.append(f"Valuation: {web_intel.valuation}")
        if web_intel.company_profile:
            for m in web_intel.company_profile.key_metrics:
                facts.append(f"{m.label}: {m.value}")

    tracxn_facts = _extract_tracxn_facts(tracxn_data)
    all_facts = (facts + tracxn_facts)[:14]

    # Build minimal financials from web intel
    yearly = web_intel.yearly_financials if web_intel else []
    company_name = (
        web_intel.company if web_intel else
        (tracxn_data.about[:30] if tracxn_data else body.company_name)
    )
    company_name = company_name or body.company_name

    # VC scoring (no real financial ratios — pass empty dict)
    scorecard, overall_score, verdict = await vc_analyst.score_company(
        company=company_name,
        key_ratios={},
        yearly_financials=[yf.model_dump() for yf in yearly],
        executive_summary=body.research_context or "",
        verified_facts=all_facts,
        audit_flags=body.audit_flags or [],
    )

    return FinancialIntelligence(
        ticker=None,
        company=company_name,
        currency="USD",
        yearly_financials=yearly,
        stock_price_history=[],
        key_ratios=None,
        vc_scorecard=scorecard,
        overall_vc_score=overall_score,
        investment_verdict=verdict,
        tracxn_data=tracxn_data,
        web_intelligence=web_intel,
        is_private=True,
    )


def _extract_tracxn_facts(tracxn_data) -> list[str]:
    """Pull useful text facts from TracxnData for VC scoring enrichment."""
    if not tracxn_data or isinstance(tracxn_data, Exception):
        return []
    facts = []
    if tracxn_data.about:
        facts.append(tracxn_data.about)
    if tracxn_data.total_funding:
        facts.append(f"Total Funding: {tracxn_data.total_funding}")
    if tracxn_data.stage:
        facts.append(f"Stage: {tracxn_data.stage}")
    for m in tracxn_data.key_metrics:
        facts.append(f"{m.label}: {m.value}")
    return facts
