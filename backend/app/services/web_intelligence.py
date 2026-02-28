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
    # Try Groq first; fall back to regex parser on any error
    if groq_client:
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
            yearly = [
                YearlyFinancial(
                    year=str(f["year"]),
                    revenue=_safe_float(f.get("revenue")),
                    net_profit=_safe_float(f.get("net_profit")),
                )
                for f in d.get("financials", [])
                if f.get("year")
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
                key_ratios=KeyRatios(),
                company_profile=company_profile,
            )
        except Exception as e:
            print(f"[WebIntel] Groq error (falling back to regex): {e}")

    # ── Regex fallback: works without any LLM ────────────────────────────────
    return _regex_parse(company_name, content)


def _regex_parse(company_name: str, content: str) -> WebIntelligence:
    """
    Extracts structured startup data from raw web snippets using regex patterns.
    No LLM required — works even when Groq is rate-limited.
    """
    import re

    def find(patterns: list[str], flags=re.IGNORECASE) -> str | None:
        for pat in patterns:
            m = re.search(pat, content, flags)
            if m:
                v = m.group(1).strip().rstrip('.').strip()
                if v and len(v) < 80:
                    return v
        return None

    def find_all(pattern: str, flags=re.IGNORECASE) -> list[str]:
        return [m.strip() for m in re.findall(pattern, content, flags) if m.strip()]

    # ── About (grab first meaningful sentence containing company name) ──
    about_match = re.search(
        rf'{re.escape(company_name)}[^.!?]{{15,300}}[.!?]',
        content, re.IGNORECASE
    )
    about = about_match.group(0).strip() if about_match else f"{company_name} — startup profile sourced from web."

    # ── Funding / valuation ──
    funding = find([
        r'raised\s+(?:a total of\s+)?([\$₹€£]\s*[\d.,]+\s*(?:million|billion|crore|lakh|M|B|Cr|K)?)',
        r'total funding[:\s]+([\$₹€£]?\s*[\d.,]+\s*(?:million|billion|crore|M|B|Cr)?)',
        r'funding of\s+([\$₹€£]?\s*[\d.,]+\s*(?:million|billion|crore|M|B|Cr)?)',
    ])
    valuation = find([
        r'valu(?:ation|ed)[:\s]+(?:at\s+)?([\$₹€£]?\s*[\d.,]+\s*(?:billion|million|crore|B|M|Cr)?)',
        r'unicorn[^.]{0,60}([\$₹€£]?\s*[\d.,]+\s*(?:billion|B))',
        r'([\$₹€£]?\s*[\d.,]+\s*(?:billion|B))\s+valu',
    ])
    stage = find([
        r'\b(Series [A-F]\+?|Pre-Seed|Seed|Angel|Series Seed|Bootstrapped|Public|Listed|IPO[\'d]?)\b',
    ])
    founded = find([r'founded in (\d{4})', r'incorporated in (\d{4})', r'est\.\s*(\d{4})'])
    hq = find([
        r'(?:headquartered|based|located)\s+in\s+([A-Z][a-zA-Z\s,]+?)(?:\.|,|\band\b)',
        r'(?:startup|company)\s+from\s+([A-Z][a-zA-Z\s,]+?)(?:\.|,)',
    ])
    employees = find([
        r'([\d,]+(?:\+|k)?)\s*employee',
        r'team of\s+([\d,]+(?:\+|k)?)',
        r'([\d,]+(?:k|\+)?)\s*people',
    ])
    revenue = find([
        r'revenue of\s+([\$₹€£]?\s*[\d.,]+\s*(?:million|billion|crore|M|B|Cr)?)',
        r'annual revenue[:\s]+([\$₹€£]?\s*[\d.,]+)',
        r'ARR of\s+([\$₹€£]?\s*[\d.,]+)',
    ])

    # ── Founders ──
    founders_raw = find_all(
        r'(?:founded by|co-founded by|founders? include)[:\s]+([A-Z][a-zA-Z\s,&]+?)(?:\.|,\s+(?:who|and|in\s+\d{4})|\band\b\s+[a-z])',
    )
    founders: list[str] = []
    for raw in founders_raw[:2]:
        for name in re.split(r',|and', raw):
            name = name.strip()
            if name and len(name.split()) <= 4 and len(name) > 2:
                founders.append(name)
    founders = list(dict.fromkeys(founders))[:5]

    # ── Investors ──
    investor_raw = find_all(
        r'(?:backed by|investors include|led by|invested by)\s+([A-Z][a-zA-Z\s,&]+?)(?:\.|,\s+[a-z])',
    )
    investors: list[str] = []
    for raw in investor_raw[:2]:
        for name in re.split(r',|and', raw):
            name = name.strip()
            if name and len(name) > 2 and len(name) < 50:
                investors.append(name)
    investors = list(dict.fromkeys(investors))[:6]

    # ── Competitors ──
    comp_patterns = [
        r'competitors?\s+(?:include|are|:)\s+([A-Za-z0-9 ,&]+?)(?:\.|and [a-z]|$)',
        r'competes?\s+with\s+([A-Za-z0-9 ,&]+?)(?:\.|and [a-z]|$)',
        r'alternatives?\s+(?:to|include)\s+([A-Za-z0-9 ,&]+?)(?:\.|$)',
        r'similar\s+to\s+([A-Za-z0-9 ,&]+?)(?:\.|$)',
    ]
    competitors: list[TracxnCompetitor] = []
    seen_comps: set[str] = set()
    for pat in comp_patterns:
        for match in re.findall(pat, content, re.IGNORECASE):
            for name in re.split(r',|and', match):
                name = name.strip()
                if name and len(name) < 40 and name.lower() != company_name.lower() and name not in seen_comps:
                    seen_comps.add(name)
                    competitors.append(TracxnCompetitor(name=name))
        if len(competitors) >= 6:
            break
    competitors = competitors[:8]

    # ── Key metrics ──
    metric_patterns = [
        (r'([\d,\.]+\s*(?:million|billion|crore|M|B|Cr)?)\s+(?:monthly\s+)?(?:active\s+)?users?', 'Monthly Active Users'),
        (r'GMV of\s+([\$₹€£]?\s*[\d,\.]+\s*(?:crore|million|billion|Cr|M|B)?)', 'GMV'),
        (r'([\d,\.]+)\s*(?:daily\s+)?orders\s+per\s+(?:day|month)', 'Orders/Day'),
        (r'([\d,\.]+\s*(?:million|billion|M|B)?)\s+(?:registered\s+)?customers?', 'Customers'),
        (r'NPS\s+(?:of\s+|score\s+)?([\d\.]+)', 'NPS Score'),
        (r'growth\s+(?:rate\s+)?of\s+([\d\.]+%)', 'Growth Rate'),
        (r'market\s+share\s+(?:of\s+)?([\d\.]+%)', 'Market Share'),
    ]
    metrics = []
    for pat, label in metric_patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            metrics.append(TracxnMetric(label=label, value=m.group(1).strip()))

    # ── Industry from keywords ──
    industry_keywords = {
        'quick commerce': 'Quick Commerce', 'food delivery': 'Food Delivery',
        'fintech': 'Fintech', 'edtech': 'EdTech', 'healthtech': 'HealthTech',
        'saas': 'SaaS', 'e-commerce': 'E-Commerce', 'logistics': 'Logistics',
        'insurtech': 'InsurTech', 'd2c': 'D2C', 'agritech': 'AgriTech',
        'proptech': 'PropTech', 'gaming': 'Gaming', 'ai': 'Artificial Intelligence',
    }
    industry = None
    content_lower = content.lower()
    for kw, label in industry_keywords.items():
        if kw in content_lower:
            industry = label
            break

    company_profile = TracxnData(
        source_url="https://web-search",
        about=about,
        founded_year=founded,
        headquarters=hq,
        stage=stage,
        total_funding=funding,
        key_metrics=metrics,
        competitors=competitors,
    )

    return WebIntelligence(
        company=company_name,
        industry=industry,
        business_model=None,
        annual_revenue=revenue,
        employee_count=employees,
        valuation=valuation,
        founders=founders,
        investors=investors,
        products=[],
        recent_news=None,
        yearly_financials=[],
        key_ratios=KeyRatios(),
        company_profile=company_profile,
    )


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
