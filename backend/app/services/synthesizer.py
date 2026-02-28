import json
from groq import AsyncGroq
from app.config import settings
from app.models.schemas import SourceItem, ResearchReport
from app.utils.helpers import strip_json_codeblock

client = None
if settings.GROQ_API_KEY:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)


async def synthesize_report(
    query: str,
    sources: list[SourceItem],
    freshness: float,
    confidence: float
) -> ResearchReport:
    """
    Synthesizes the final structured report using the Groq LLM.
    """
    if not client:
        print(f"Warning: GROQ_API_KEY not set. Returning mock report for: {query}")
        return ResearchReport(
            executive_summary=f"Mock summary for '{query}'.",
            key_findings=[{"title": "Finding 1", "description": "Mock finding."}],
            risks_and_uncertainties=[{"title": "Risk 1", "description": "Mock risk."}],
            strategic_implications=[{"title": "Implication 1", "description": "Mock implication."}],
            sources=sources,
            confidence_score=confidence,
            freshness_index=freshness
        )

    sources_text = ""
    for idx, s in enumerate(sources):
        sources_text += (
            f"[{idx+1}] Title: {s.title}\n"
            f"    URL: {s.url}\n"
            f"    Date: {s.published_date}\n"
            f"    Credibility: {s.score}/10\n"
            f"    Snippet: {s.snippet}\n\n"
        )

    prompt = f"""You are an elite Strategy Consultant and Research Analyst. Based on the query and intelligence below, produce a high-quality, professional research report.

User Query: "{query}"

Retrieved Intelligence:
{sources_text}

Respond ONLY with valid JSON matching this exact schema:
{{
  "executive_summary": "2-3 paragraph high-level summary.",
  "key_findings": [
    {{"title": "...", "description": "... cite sources as [1], [2] etc."}}
  ],
  "risks_and_uncertainties": [
    {{"title": "...", "description": "..."}}
  ],
  "strategic_implications": [
    {{"title": "...", "description": "..."}}
  ]
}}

No markdown, no extra text, only the JSON object.
    """

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )

        content = strip_json_codeblock(response.choices[0].message.content)
        data = json.loads(content)

        return ResearchReport(
            executive_summary=data.get("executive_summary", "No summary provided."),
            key_findings=data.get("key_findings", []),
            risks_and_uncertainties=data.get("risks_and_uncertainties", []),
            strategic_implications=data.get("strategic_implications", []),
            sources=sources,
            confidence_score=confidence,
            freshness_index=freshness
        )

    except Exception as e:
        print(f"Error in synthesize_report: {e}")
        return ResearchReport(
            executive_summary=f"Failed to generate report. Query: {query}",
            key_findings=[],
            risks_and_uncertainties=[],
            strategic_implications=[],
            sources=sources,
            confidence_score=confidence,
            freshness_index=freshness
        )
