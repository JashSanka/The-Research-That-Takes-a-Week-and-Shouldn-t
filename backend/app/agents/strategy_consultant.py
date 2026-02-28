import json
from groq import AsyncGroq
from app.config import settings
from app.models.schemas import (
    SeniorAnalystOutput, StrategyConsultantOutput,
    KeyFinding, RiskUncertainty,
)
from app.utils.helpers import strip_json_codeblock

client = None
if settings.GROQ_API_KEY:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """You are a Strategy Consultant at a top-tier global consulting firm.
You specialize in converting raw, multi-source research data into clear,
structured, decision-ready intelligence reports for senior business leaders.
You will receive the original user query and evaluated research output from multiple dimensions.
Your job is to synthesize this into a polished, structured report.

INSTRUCTIONS:
Using the verified facts, agreements, and contradiction flags provided:
- Write a concise Executive Summary in 3 to 5 sentences written for a C-suite audience
- List Key Findings — one per research dimension — written as analytical insights, not raw facts
- Derive Strategic Implications: what does this data mean for decision-making? (3-5 actionable points)
- List all Risks and Uncertainties, especially those from contradictions or low-credibility data
- Do not fabricate data. Only use what is present in the input.
- Insights must go beyond restating facts — they must provide analytical value.
- Every risk must reference where the uncertainty came from.
- Clean up any markdown syntax (##, **, *) in the input before using it.

OUTPUT RULES:
- Return ONLY a valid JSON object. No text, no commentary outside the JSON.
- Strategic implications must be actionable and specific.
- Key findings must be readable sentences, NOT raw data snippets.

OUTPUT FORMAT:
{
  "original_query": "<user's original query>",
  "executive_summary": "<3 to 5 sentence C-suite level summary>",
  "key_findings": [
    {
      "dimension": "<human-readable dimension name e.g. Market Size>",
      "finding": "<analytical insight written as a clean sentence>",
      "supporting_sources": ["<url1>", "<url2>"]
    }
  ],
  "strategic_implications": [
    "<actionable implication 1>",
    "<actionable implication 2>",
    "<actionable implication 3>"
  ],
  "risks_and_uncertainties": [
    {
      "risk": "<clear description of the risk>",
      "origin": "<contradiction | low credibility source | data gap>"
    }
  ]
}"""


def _compress_senior_output(so: SeniorAnalystOutput) -> dict:
    """
    Compress a SeniorAnalystOutput to under ~500 tokens for the strategy consultant.
    Strips markdown, truncates long snippets, only passes essential fields.
    """
    import re

    def clean(text: str) -> str:
        """Remove markdown symbols and truncate."""
        text = re.sub(r'[#*_`\[\]>]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:300]  # Max 300 chars per fact

    return {
        "dimension": so.sub_question_id,
        "sub_question": so.sub_question,
        "verified_facts": [clean(f) for f in so.verified_key_facts[:3]],  # top 3 only
        "agreements": [clean(a) for a in so.agreements[:2]],
        "contradictions": [
            {
                "a": clean(c.claim_a),
                "b": clean(c.claim_b),
                "stronger": c.stronger_signal,
            }
            for c in so.contradictions[:2]
        ],
        "top_sources": [
            e.url for e in sorted(
                so.source_evaluations, key=lambda x: x.credibility_score, reverse=True
            )[:3]
        ],
    }


async def synthesize(
    query: str,
    senior_outputs: list[SeniorAnalystOutput],
) -> StrategyConsultantOutput:
    """
    Agent 3 — Strategy Consultant.
    Synthesizes all Senior Analyst outputs into a structured intelligence report.
    """
    # Compress input to avoid token limits
    compressed = [_compress_senior_output(so) for so in senior_outputs]

    user_message = (
        f"Original Query: {query}\n\n"
        f"Evaluated Research Data:\n{json.dumps(compressed, indent=2)}"
    )

    if not client:
        return _fallback_output(query, senior_outputs)

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        content = strip_json_codeblock(raw)
        data = json.loads(content)

        key_findings = [
            KeyFinding(
                dimension=f.get("dimension", ""),
                finding=f.get("finding", ""),
                supporting_sources=f.get("supporting_sources", []),
            )
            for f in data.get("key_findings", [])
            if f.get("finding")  # Skip empty findings
        ]

        risks = [
            RiskUncertainty(
                risk=r.get("risk", ""),
                origin=r.get("origin", ""),
            )
            for r in data.get("risks_and_uncertainties", [])
            if r.get("risk")
        ]

        implications = [s for s in data.get("strategic_implications", []) if s]

        if not key_findings and not implications:
            print("[StrategyConsultant] LLM returned empty content — using fallback")
            return _fallback_output(query, senior_outputs)

        return StrategyConsultantOutput(
            original_query=data.get("original_query", query),
            executive_summary=data.get("executive_summary", ""),
            key_findings=key_findings,
            strategic_implications=implications,
            risks_and_uncertainties=risks,
        )

    except Exception as e:
        print(f"[StrategyConsultant] Error: {e}")
        return _fallback_output(query, senior_outputs)


def _fallback_output(query: str, senior_outputs: list[SeniorAnalystOutput]) -> StrategyConsultantOutput:
    """
    Improved fallback: builds a readable report from verified facts without raw IDs.
    """
    import re

    def clean(text: str) -> str:
        text = re.sub(r'[#*_`\[\]>]', '', text)
        return re.sub(r'\s+', ' ', text).strip()[:250]

    # Map sq_N IDs to their actual dimension/sub-question
    findings = []
    for so in senior_outputs:
        best_fact = next(
            (clean(f) for f in so.verified_key_facts if f.strip()), None
        )
        if not best_fact:
            best_fact = next(
                (clean(e.key_fact_extracted) for e in so.source_evaluations if e.key_fact_extracted.strip()),
                "No significant facts extracted for this dimension."
            )
        findings.append(KeyFinding(
            dimension=so.sub_question,  # Use the actual sub-question, not sq_N
            finding=best_fact,
            supporting_sources=[e.url for e in so.source_evaluations[:2]],
        ))

    all_contradictions = [
        RiskUncertainty(
            risk=f"Conflicting data found: '{clean(c.claim_a)}' vs '{clean(c.claim_b)}'",
            origin="contradiction",
        )
        for so in senior_outputs
        for c in so.contradictions[:1]  # Max 1 per dimension
    ]

    return StrategyConsultantOutput(
        original_query=query,
        executive_summary=(
            f"Analysis of '{query}' drew on {sum(len(so.sources) for so in senior_outputs)} sources "
            f"across {len(senior_outputs)} research dimensions. "
            f"{sum(len(so.verified_key_facts) for so in senior_outputs)} facts were verified "
            f"from credible sources. "
            f"Key findings and contradictions across dimensions are listed below."
        ),
        key_findings=findings,
        strategic_implications=[
            "Validate the findings below against primary sources before making investment decisions.",
            "Cross-reference any contradicted claims with authoritative industry reports.",
            "Monitor recent regulatory and competitive developments closely.",
        ],
        risks_and_uncertainties=all_contradictions or [
            RiskUncertainty(
                risk="Insufficient high-credibility sources were available for full synthesis.",
                origin="data gap",
            )
        ],
    )
