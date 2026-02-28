"""
Tracxn Scraper — fetches company intelligence from tracxn.com via Tavily search.

Strategy:
  1. Search Tavily for "tracxn {company_name} company profile" (not site: prefix)
  2. Collect all tracxn.com result snippets (about page + funding page + competitors page)
  3. Feed all snippets to Groq for structured extraction
  This avoids using Tavily extract (which is blocked by Tracxn's auth wall).
"""
import json
import re
from tavily import AsyncTavilyClient
from groq import AsyncGroq
from app.config import settings
from app.models.schemas import TracxnData, TracxnMetric, TracxnCompetitor
from app.utils.helpers import strip_json_codeblock

tavily_client = None
if settings.TAVILY_API_KEY:
    tavily_client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)

groq_client = None
if settings.GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

PARSE_SYSTEM = """You are a data extraction assistant. Extract structured company information
from multiple Tracxn search result snippets provided below.

Return ONLY a valid JSON object with this exact structure:
{
  "about": "<2-4 sentence summary of what the company does, from the content>",
  "founded_year": "<year as string or null>",
  "headquarters": "<city, country or null>",
  "stage": "<e.g. Series D / Public / Seed or null>",
  "total_funding": "<e.g. $1.2B or null>",
  "key_metrics": [
    { "label": "<metric name>", "value": "<metric value>" }
  ],
  "competitors": [
    { "name": "<competitor name>", "description": "<1 sentence or null>", "url": "<url or null>" }
  ]
}

Rules:
- key_metrics: extract quantitative data (GMV, users, orders, revenue, growth rate, employees, valuation) — up to 8
- competitors: ONLY list companies that are PRODUCT or SERVICE competitors (same market). 
  DO NOT include investors, VCs, asset management companies, or financial institutions.
  Examples of valid competitors for a food delivery app: Swiggy, Deliveroo, UberEats, DoorDash.
  Examples to EXCLUDE: Fidelity, ICICI Prudential, Sequoia, Tiger Global.
- stage: look for "Public", "Series X", "Seed", "Unfunded" etc.
- If a field is absent from the content, use null for scalars and [] for arrays
- Return ONLY the JSON object, no other text"""


async def fetch_tracxn_data(company_name: str) -> TracxnData | None:
    """
    Searches Tavily for Tracxn snippets about the company and parses structured data.
    Uses multiple search queries to maximize coverage.
    """
    if not tavily_client:
        print("[Tracxn] Tavily client not configured.")
        return None

    # ── Step 1: Run two targeted searches in parallel ─────────────────────────
    import asyncio

    queries = [
        f'site:tracxn.com "{company_name}" company profile founded stage funding',
        f'tracxn.com "{company_name}" top competitors alternatives similar companies food delivery',
    ]

    try:
        tasks = [
            tavily_client.search(
                query=q,
                search_depth="basic",
                max_results=5,
                include_answer=False,
            )
            for q in queries
        ]
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"[Tracxn] Search error: {e}")
        return None

    # ── Step 2: Collect all tracxn.com snippets + find best URL ──────────────
    all_snippets: list[str] = []
    tracxn_url: str | None = None

    for result in search_results:
        if isinstance(result, Exception):
            continue
        for r in result.get("results", []):
            url = r.get("url", "")
            content = r.get("content", "").strip()
            if "tracxn.com" in url and content:
                all_snippets.append(f"[Source: {url}]\n{content}")
                # Prefer the main company page URL (not funding/sub-pages)
                if (
                    "/d/companies/" in url
                    and company_name.lower().replace(" ", "") in url.lower()
                    and tracxn_url is None
                ):
                    tracxn_url = url

    if not all_snippets:
        print(f"[Tracxn] No Tracxn snippets found for {company_name}")
        return None

    if not tracxn_url:
        # Fall back to first tracxn URL found
        for result in search_results:
            if isinstance(result, Exception):
                continue
            for r in result.get("results", []):
                if "tracxn.com" in r.get("url", ""):
                    tracxn_url = r["url"]
                    break
            if tracxn_url:
                break

    if not tracxn_url:
        tracxn_url = "https://tracxn.com"

    combined_content = "\n\n".join(all_snippets)[:5000]
    print(f"[Tracxn] Collected {len(all_snippets)} snippets for {company_name}, URL: {tracxn_url}")

    # ── Step 3: Parse structured data ─────────────────────────────────────────
    return await _parse_with_groq(company_name, tracxn_url, combined_content)


async def _parse_with_groq(
    company_name: str,
    source_url: str,
    combined_snippets: str,
) -> TracxnData | None:

    # Pre-extract competitor names from snippet text using the known Tracxn format:
    # "top competitors include X, Y and Z" or "Logo for X. X. 2008, City, Stage."
    competitor_seed: list[str] = []

    # Pattern 1: "top competitors include X, Y"
    m1 = re.findall(
        r'top competitors?\s+(?:include|are|:)\s+([A-Za-z0-9 ,&\-]+?)(?:\.|$)',
        combined_snippets, re.IGNORECASE
    )
    for match in m1:
        for name in re.split(r',|and', match):
            name = name.strip()
            if name and len(name) < 40 and name.lower() != company_name.lower():
                competitor_seed.append(name)

    # Pattern 2: Tracxn snippet format "Logo for X. X. year, city, stage"
    m2 = re.findall(r'Logo for ([A-Za-z0-9 &\-]+)\.\s+\1', combined_snippets)
    for name in m2:
        name = name.strip()
        if name and len(name) < 40 and name.lower() != company_name.lower():
            competitor_seed.append(name)

    # Deduplicate
    competitor_seed = list(dict.fromkeys(competitor_seed))[:10]

    if not groq_client:
        # Build TracxnData from pre-extracted data + fallback
        td = _fallback_parse(company_name, source_url, combined_snippets)
        if competitor_seed and not td.competitors:
            td.competitors = [TracxnCompetitor(name=n) for n in competitor_seed]
        return td

    # Include pre-extracted competitors explicitly in the prompt
    seeded_section = ""
    if competitor_seed:
        seeded_section = f"\n\nPre-extracted Competitors from snippets (include these): {', '.join(competitor_seed)}"

    user_message = (
        f"Company: {company_name}\n\n"
        f"Tracxn Search Snippets:\n{combined_snippets}"
        f"{seeded_section}"
    )

    try:
        response = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": PARSE_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        content = strip_json_codeblock(response.choices[0].message.content)
        data = json.loads(content)

        metrics = [
            TracxnMetric(label=m.get("label", ""), value=m.get("value", ""))
            for m in data.get("key_metrics", [])
            if m.get("label") and m.get("value")
        ]
        competitors = [
            TracxnCompetitor(
                name=c.get("name", ""),
                description=c.get("description"),
                url=c.get("url"),
            )
            for c in data.get("competitors", [])
            if c.get("name")
        ]

        return TracxnData(
            source_url=source_url,
            about=data.get("about") or f"{company_name} company intelligence from Tracxn.",
            founded_year=data.get("founded_year"),
            headquarters=data.get("headquarters"),
            stage=data.get("stage"),
            total_funding=data.get("total_funding"),
            key_metrics=metrics,
            competitors=competitors,
        )

    except Exception as e:
        print(f"[Tracxn] Groq parse error: {e}")
        return _fallback_parse(company_name, source_url, combined_snippets)


def _fallback_parse(company_name: str, source_url: str, content: str) -> TracxnData:
    """Parse what we can from snippets without LLM."""

    def find_val(labels: list[str]) -> str | None:
        for label in labels:
            m = re.search(rf'{label}[:\s]+([^\n\|,\.]+)', content, re.IGNORECASE)
            if m:
                v = m.group(1).strip()
                if len(v) < 60:
                    return v
        return None

    # Extract competitors from the snippet text
    competitor_matches = re.findall(
        r'(?:top competitors?|alternatives?)[^\n]*include:?\s*([^\n]+)',
        content, re.IGNORECASE
    )
    competitors = []
    if competitor_matches:
        for part in re.split(r'[,;]', competitor_matches[0])[:8]:
            name = part.strip().strip('.')
            if name and len(name) < 60:
                competitors.append(TracxnCompetitor(name=name))

    # Extract a reasonable about text
    about_match = re.search(
        r'(?:platform|company|service|solution|app)[^.]{20,300}\.', 
        content, re.IGNORECASE
    )
    about = about_match.group(0) if about_match else f"{company_name} — data sourced from Tracxn."

    return TracxnData(
        source_url=source_url,
        about=about,
        founded_year=find_val(["founded", "incorporated", "established"]),
        headquarters=find_val(["headquartered", "based in", "location", "headquarters"]),
        stage=find_val(["stage", "funding stage", "round"]),
        total_funding=find_val(["total funding", "raised", "funding raised"]),
        key_metrics=[],
        competitors=competitors,
    )
