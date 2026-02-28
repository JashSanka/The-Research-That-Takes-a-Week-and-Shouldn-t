"""
Web Intelligence — Universal company data fetcher for private/micro startups.

For companies not on Yahoo Finance or Tracxn, this fetches data from:
  - Crunchbase, AngelList, LinkedIn, Product Hunt
  - Inc42, YourStory, TechCrunch, Moneycontrol (India), Economic Times
  - Company website / press releases

Flow:
  1. Run 3 parallel Tavily searches targeting startup databases
  2. Combine all snippets
  3. Use Groq to extract structured intelligence
"""
import json
import asyncio
from tavily import AsyncTavilyClient
from groq import AsyncGroq
from app.config import settings
from app.models.schemas import (
    WebIntelligence, YearlyFinancial, KeyRatios, TracxnData,
    TracxnMetric, TracxnCompetitor, VCDimensionScore
)
from app.utils.helpers import strip_json_codeblock

tavily_client = None
if settings.TAVILY_API_KEY:
    tavily_client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)

groq_client = None
if settings.GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


EXTRACT_SYSTEM = """You are a startup intelligence analyst. Extract structured information
about a company from web search snippets (Crunchbase, LinkedIn, Inc42, YourStory, TechCrunch, etc.)

Return ONLY a valid JSON object with this exact structure:
{
  "company_display_name": "<official company name>",
  "about": "<2-4 sentence company description>",
  "founded_year": "<year or null>",
  "headquarters": "<city, country or null>",
  "stage": "<Bootstrapped / Pre-Seed / Seed / Series A / Series B / Series C+ / Public / null>",
  "total_funding": "<e.g. $2.5M or ₹10Cr or null>",
  "valuation": "<estimated valuation or null>",
  "industry": "<primary industry/sector>",
  "business_model": "<B2B / B2C / B2B2C / SaaS / Marketplace / etc.>",
  "annual_revenue": "<revenue figure with currency or null>",
  "employee_count": "<headcount or range or null>",
  "key_metrics": [
    {"label": "<metric>", "value": "<value>"}
  ],
  "financials": [
    {"year": "<YYYY>", "revenue": <number or null>, "net_profit": <number or null>}
  ],
  "competitors": [
    {"name": "<competitor>", "description": "<1 sentence or null>"}
  ],
  "investors": ["<investor names>"],
  "founders": ["<founder names>"],
  "products": ["<key products or services>"],
  "recent_news": "<one line about latest significant news or null>"
}

Rules:
- key_metrics: up to 8 items — GMV, MAU, DAU, orders/day, NPS, churn, growth rate, etc.
- financials: if specific yearly numbers are found, include them; otherwise empty array []
- competitors: ONLY product/service competitors in same market, NOT investors — up to 8
- If a field is absent from the content, use null
- Return ONLY the JSON, no other text"""


async def fetch_web_intelligence(company_name: str) -> WebIntelligence | None:
    """
    Searches multiple startup intelligence sources for a company
    and returns structured data. Works for private/micro startups.
    """
    if not tavily_client:
        return None

    queries = [
        f'"{company_name}" startup funding valuation revenue crunchbase angellist',
        f'"{company_name}" company founders product competitors india OR global',
        f'"{company_name}" inc42 OR yourstory OR techcrunch OR linkedin company overview',
    ]

    try:
        tasks = [
            tavily_client.search(
                query=q,
                search_depth="advanced",   # deeper for small companies
                max_results=5,
                include_answer=False,
            )
            for q in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"[WebIntel] Search error: {e}")
        return None

    # Collect all snippets
    snippets: list[str] = []
    for batch in results:
        if isinstance(batch, Exception):
            continue
        for r in batch.get("results", []):
            content = r.get("content", "").strip()
            url = r.get("url", "")
            if content:
                snippets.append(f"[{url}]\n{content}")

    if not snippets:
        print(f"[WebIntel] No snippets for {company_name}")
        return None

    combined = "\n\n".join(snippets)[:7000]
    print(f"[WebIntel] {len(snippets)} snippets for {company_name}")

    return await _parse_web_intelligence(company_name, combined)


async def _parse_web_intelligence(company_name: str, content: str) -> WebIntelligence | None:
    if not groq_client:
        return None

    try:
        response = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM},
                {"role": "user", "content": f"Company: {company_name}\n\n{content}"},
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        raw = strip_json_codeblock(response.choices[0].message.content)
        d = json.loads(raw)

        # Build yearly financials from parsed data
        yearly: list[YearlyFinancial] = []
        for f in d.get("financials", []):
            if f.get("year"):
                yearly.append(YearlyFinancial(
                    year=str(f["year"]),
                    revenue=_safe_float(f.get("revenue")),
                    net_profit=_safe_float(f.get("net_profit")),
                ))

        # Build key ratios
        key_ratios = KeyRatios(
            revenue_growth_yoy=None,
            profit_margin=None,
        )

        # Build TracxnData-like profile
        metrics = [
            TracxnMetric(label=m["label"], value=str(m["value"]))
            for m in d.get("key_metrics", [])
            if m.get("label") and m.get("value")
        ]
        competitors = [
            TracxnCompetitor(name=c["name"], description=c.get("description"))
            for c in d.get("competitors", [])
            if c.get("name")
        ]

        company_profile = TracxnData(
            source_url="https://web-search",
            about=d.get("about") or f"{company_name} — startup profile",
            founded_year=d.get("founded_year"),
            headquarters=d.get("headquarters"),
            stage=d.get("stage"),
            total_funding=d.get("total_funding"),
            key_metrics=metrics,
            competitors=competitors,
        )

        return WebIntelligence(
            company=d.get("company_display_name") or company_name,
            industry=d.get("industry"),
            business_model=d.get("business_model"),
            annual_revenue=d.get("annual_revenue"),
            employee_count=d.get("employee_count"),
            valuation=d.get("valuation"),
            founders=d.get("founders", []),
            investors=d.get("investors", []),
            products=d.get("products", []),
            recent_news=d.get("recent_news"),
            yearly_financials=yearly,
            key_ratios=key_ratios,
            company_profile=company_profile,
        )

    except Exception as e:
        print(f"[WebIntel] Parse error: {e}")
        return None


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
