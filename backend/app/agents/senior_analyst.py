import json
from groq import AsyncGroq
from app.config import settings
from app.models.schemas import (
    SourceItem, SubQuestionPlan, SeniorAnalystOutput,
    SourceEvaluation, Contradiction,
)
from app.utils.helpers import strip_json_codeblock

client = None
if settings.GROQ_API_KEY:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """You are a Senior Research Analyst with deep expertise in evaluating the quality,
credibility, and reliability of information retrieved from the web.
You will receive a sub-question and a list of raw sources retrieved from the internet.
Your job is to critically evaluate each source and extract only what can be trusted.

INSTRUCTIONS:
For each source provided:
- Assign a credibility_score from 0 to 10 based on domain type:
    .gov or .edu                                          = 8 to 10
    Major news outlets (Reuters, Bloomberg, NYT, BBC)    = 6 to 8
    Industry reports or corporate sites                  = 5 to 7
    Blogs, forums, unknown domains                       = 1 to 4
- Assign a recency_score from 0 to 10 based on publication date:
    Less than 1 month old   = 9 to 10
    1 to 6 months old       = 6 to 8
    6 to 12 months old      = 4 to 6
    Older than 1 year       = 1 to 3
    No date available       = 3
- Extract the single most important fact or claim from each source
- Identify facts confirmed by 2 or more sources (agreements)
- Identify facts where sources directly contradict each other (contradictions)
- Only include a fact in verified_key_facts if it comes from a source with credibility_score >= 6

OUTPUT RULES:
- Return ONLY a valid JSON object. No text, no commentary outside the JSON.
- Do not fabricate facts or scores.
- If a source has no clear publication date, assign recency_score 3.

OUTPUT FORMAT:
{
  "sub_question_id": "<same id as received>",
  "sub_question": "<the sub-question being evaluated>",
  "source_evaluations": [
    {
      "url": "<source url>",
      "domain_type": "<gov|edu|major_news|industry|blog|unknown>",
      "credibility_score": 7.5,
      "recency_score": 8.0,
      "key_fact_extracted": "<most important fact from this source>"
    }
  ],
  "agreements": ["<fact confirmed by 2+ sources>"],
  "contradictions": [
    {
      "claim_a": "<claim>",
      "source_a": "<url>",
      "claim_b": "<claim>",
      "source_b": "<url>",
      "stronger_signal": "<url of more credible source>"
    }
  ],
  "verified_key_facts": ["<fact from credibility >= 6 source>"]
}"""


async def evaluate(sq: SubQuestionPlan, sources: list[SourceItem]) -> SeniorAnalystOutput:
    """
    Agent 2 — Senior Analyst.
    Critically evaluates sources for a single sub-question.
    """
    if not sources:
        return _empty_output(sq)

    sources_json = json.dumps([
        {
            "url": s.url,
            "title": s.title,
            "published_date": s.published_date or "unknown",
            "snippet": s.snippet,
        }
        for s in sources
    ], indent=2)

    user_message = (
        f"Sub-question: {sq.sub_question}\n\n"
        f"Sources:\n{sources_json}"
    )

    if not client:
        return _fallback_output(sq, sources)

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        content = strip_json_codeblock(response.choices[0].message.content)
        data = json.loads(content)

        evals = [
            SourceEvaluation(
                url=e.get("url", ""),
                domain_type=e.get("domain_type", "unknown"),
                credibility_score=float(e.get("credibility_score", 5.0)),
                recency_score=float(e.get("recency_score", 3.0)),
                key_fact_extracted=e.get("key_fact_extracted", ""),
            )
            for e in data.get("source_evaluations", [])
        ]

        contradictions = [
            Contradiction(
                claim_a=c.get("claim_a", ""),
                source_a=c.get("source_a", ""),
                claim_b=c.get("claim_b", ""),
                source_b=c.get("source_b", ""),
                stronger_signal=c.get("stronger_signal", ""),
            )
            for c in data.get("contradictions", [])
        ]

        return SeniorAnalystOutput(
            sub_question_id=sq.sub_question_id,
            sub_question=sq.sub_question,
            sources=sources,
            source_evaluations=evals,
            agreements=data.get("agreements", []),
            contradictions=contradictions,
            verified_key_facts=data.get("verified_key_facts", []),
        )

    except Exception as e:
        print(f"[SeniorAnalyst] Error on {sq.sub_question_id}: {e}")
        return _fallback_output(sq, sources)


def _empty_output(sq: SubQuestionPlan) -> SeniorAnalystOutput:
    return SeniorAnalystOutput(
        sub_question_id=sq.sub_question_id,
        sub_question=sq.sub_question,
        sources=[],
        source_evaluations=[],
        agreements=[],
        contradictions=[],
        verified_key_facts=[],
    )


def _fallback_output(sq: SubQuestionPlan, sources: list[SourceItem]) -> SeniorAnalystOutput:
    evals = [
        SourceEvaluation(
            url=s.url,
            domain_type="unknown",
            credibility_score=5.0,
            recency_score=5.0,
            key_fact_extracted=s.snippet[:200] if s.snippet else "No content.",
        )
        for s in sources
    ]
    return SeniorAnalystOutput(
        sub_question_id=sq.sub_question_id,
        sub_question=sq.sub_question,
        sources=sources,
        source_evaluations=evals,
        agreements=[],
        contradictions=[],
        verified_key_facts=[e.key_fact_extracted for e in evals],
    )
