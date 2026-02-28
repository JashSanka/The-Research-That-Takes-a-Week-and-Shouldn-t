"""
Agent 5 — VC Analyst
Scores a company across 10 investment dimensions using
research context + financial metrics. Returns a VC Scorecard.
"""
import json
from groq import AsyncGroq
from app.config import settings
from app.models.schemas import VCDimensionScore
from app.utils.helpers import strip_json_codeblock

client = None
if settings.GROQ_API_KEY:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

VC_DIMENSIONS = [
    "Market Opportunity",
    "Market Timing",
    "Business Model Quality",
    "Financial Health",
    "Growth Trajectory",
    "Competitive Position",
    "Founder & Team",
    "Product Differentiation",
    "Exit Potential",
    "Risk & Red Flags",
]

SYSTEM_PROMPT = """You are an elite VC Analyst at a top-tier venture capital firm (think Sequoia, a16z).
You will receive research data and financial metrics about a company.
Score the company across exactly 10 investment dimensions.

SCORING RULES:
- Score 1–10 for each dimension (10 = exceptional, 1 = serious red flag)
- Assign verdict: "Strong" (8–10), "Moderate" (5–7), "Weak" (1–4), "Unknown" (if data insufficient → score 5)
- Keep rationale to 1–2 sentences, specific and data-driven
- Be honest — do not inflate scores. Red flags should score low.
- If information for a dimension is missing from the inputs, use "Unknown" as verdict with score 5

DIMENSIONS YOU MUST SCORE (in this order):
1. Market Opportunity — TAM size, market growth rate, tailwinds
2. Market Timing — Why now? Regulatory/tech/cultural shifts?
3. Business Model Quality — Revenue quality, gross margins, recurring vs one-time, unit economics
4. Financial Health — Profitability or path to it, debt levels, cash position, burn rate
5. Growth Trajectory — Revenue YoY growth, user growth, expansion metrics
6. Competitive Position — Market share, defensibility, switching costs, moat
7. Founder & Team — Domain expertise, execution track record, coachability
8. Product Differentiation — 10x better? Network effects? Proprietary data?
9. Exit Potential — Logical acquirers, IPO path, sector comparable exits
10. Risk & Red Flags — Contradictions in data, regulatory risk, key person risk, vanity metrics

OUTPUT RULES:
- Return ONLY a valid JSON array of exactly 10 objects
- Do not include any text outside the JSON array

OUTPUT FORMAT:
[
  {
    "dimension": "Market Opportunity",
    "score": 8,
    "verdict": "Strong",
    "rationale": "<1-2 sentences specific to this company>"
  }
]"""


async def score_company(
    company: str,
    key_ratios: dict,
    yearly_financials: list[dict],
    executive_summary: str,
    verified_facts: list[str],
    audit_flags: list[str],
) -> tuple[list[VCDimensionScore], float, str]:
    """
    Returns (scorecard, overall_score, investment_verdict).
    """
    # Build a compact financials summary for the prompt
    fin_lines = []
    for yf_data in yearly_financials[:4]:
        parts = [f"Year {yf_data.get('year', '?')}:"]
        if yf_data.get("revenue"):
            parts.append(f"Revenue={yf_data['revenue']}")
        if yf_data.get("net_profit"):
            parts.append(f"NetProfit={yf_data['net_profit']}")
        if yf_data.get("gross_margin"):
            parts.append(f"GrossMargin={yf_data['gross_margin']}%")
        if yf_data.get("eps"):
            parts.append(f"EPS={yf_data['eps']}")
        fin_lines.append(" ".join(parts))

    ratios_text = ", ".join([
        f"{k}={v}" for k, v in key_ratios.items() if v is not None
    ])

    facts_text = "\n".join(f"- {f}" for f in (verified_facts or [])[:10])
    flags_text = "; ".join(audit_flags) if audit_flags else "None"

    user_message = (
        f"Company: {company}\n\n"
        f"Key Financial Ratios: {ratios_text or 'Not available'}\n\n"
        f"Financial History:\n{chr(10).join(fin_lines) or 'Not available'}\n\n"
        f"Research Summary: {executive_summary[:600]}\n\n"
        f"Key Verified Facts:\n{facts_text or 'None'}\n\n"
        f"Audit Flags: {flags_text}"
    )

    scorecard: list[VCDimensionScore] = []

    if not client:
        return _fallback_scorecard(), 5.0, "Insufficient Data"

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        content = strip_json_codeblock(response.choices[0].message.content)

        # Handle both array and object wrapping
        data = json.loads(content)
        if isinstance(data, dict):
            data = data.get("scorecard") or data.get("scores") or list(data.values())[0]

        for item in data:
            scorecard.append(VCDimensionScore(
                dimension=item.get("dimension", "Unknown"),
                score=max(1, min(10, int(item.get("score", 5)))),
                verdict=item.get("verdict", "Unknown"),
                rationale=item.get("rationale", ""),
            ))

    except Exception as e:
        print(f"[VCAnalyst] Error: {e}")
        scorecard = _fallback_scorecard()

    if not scorecard:
        scorecard = _fallback_scorecard()

    # Weighted overall score (Financial Health and Growth Trajectory have higher weight)
    weights = {
        "Market Opportunity": 1.5,
        "Business Model Quality": 1.5,
        "Financial Health": 1.5,
        "Growth Trajectory": 1.5,
        "Competitive Position": 1.2,
        "Risk & Red Flags": 1.3,
        "Market Timing": 0.8,
        "Founder & Team": 1.0,
        "Product Differentiation": 1.0,
        "Exit Potential": 0.7,
    }
    total_weight = 0
    weighted_sum = 0
    for s in scorecard:
        w = weights.get(s.dimension, 1.0)
        weighted_sum += s.score * w
        total_weight += w

    overall = round(weighted_sum / total_weight, 1) if total_weight else 5.0

    if overall >= 7.5:
        verdict = "Strong Investment Signal"
    elif overall >= 6.0:
        verdict = "Investigate Further"
    elif overall >= 4.5:
        verdict = "Proceed with Caution"
    else:
        verdict = "Pass"

    return scorecard, overall, verdict


def _fallback_scorecard() -> list[VCDimensionScore]:
    return [
        VCDimensionScore(
            dimension=dim,
            score=5,
            verdict="Unknown",
            rationale="Insufficient data to score this dimension.",
        )
        for dim in VC_DIMENSIONS
    ]
