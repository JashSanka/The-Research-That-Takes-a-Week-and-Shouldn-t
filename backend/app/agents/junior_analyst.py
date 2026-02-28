import json
from groq import AsyncGroq
from app.config import settings
from app.models.schemas import ResearchPlan, SubQuestionPlan
from app.utils.helpers import strip_json_codeblock

client = None
if settings.GROQ_API_KEY:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """You are a Junior Research Analyst working inside an autonomous AI research pipeline.
Your only job is to receive a complex research question from the user and break it down
into structured, focused sub-questions that can be independently searched on the web.
You do not answer questions. You do not summarize. You only decompose.

INSTRUCTIONS:
Given the user's research query, you must:
- Identify the key dimensions of the topic (e.g. market size, competition, regulation, trends, risks, funding)
- Generate exactly 5 to 7 focused sub-questions, each targeting one specific dimension
- Each sub-question must be independently searchable and non-overlapping with others
- For each sub-question, provide 3 to 4 short search keywords optimized for web retrieval
- For each sub-question, assign a tavily_topic: use "news" for recent events/regulation,
  "finance" for market/funding/investment data, "general" for all other dimensions

OUTPUT RULES:
- Return ONLY a valid JSON object
- Do not write any text, explanation, or commentary outside the JSON
- Do not answer the sub-questions. Do not make up data.

OUTPUT FORMAT:
{
  "original_query": "<exact user query>",
  "research_plan": [
    {
      "sub_question_id": "sq_1",
      "dimension": "<e.g. Market Size>",
      "sub_question": "<focused, searchable question>",
      "search_keywords": ["keyword1", "keyword2", "keyword3"],
      "tavily_topic": "finance"
    }
  ]
}"""


async def decompose(query: str) -> ResearchPlan:
    """
    Agent 1 — Junior Analyst.
    Decomposes a broad research query into 5-7 focused sub-questions,
    each enriched with search keywords and a Tavily topic tag.
    """
    if not client:
        return _fallback_plan(query)

    user_message = f"USER:\n{query}"

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        content = strip_json_codeblock(response.choices[0].message.content)
        data = json.loads(content)

        plan_items = []
        for item in data.get("research_plan", []):
            plan_items.append(SubQuestionPlan(
                sub_question_id=item.get("sub_question_id", "sq_1"),
                dimension=item.get("dimension", "General"),
                sub_question=item.get("sub_question", query),
                search_keywords=item.get("search_keywords", [query]),
                tavily_topic=item.get("tavily_topic", "general"),
            ))

        if not plan_items:
            return _fallback_plan(query)

        return ResearchPlan(
            original_query=data.get("original_query", query),
            research_plan=plan_items,
        )

    except Exception as e:
        print(f"[JuniorAnalyst] Error: {e}")
        return _fallback_plan(query)


def _fallback_plan(query: str) -> ResearchPlan:
    dimensions = [
        ("Market Size", "What is the current market size and growth trajectory?", ["market size", "growth rate", "TAM"], "finance"),
        ("Competitive Landscape", "Who are the major players and what is the competitive dynamic?", ["competitors", "market share", "industry leaders"], "general"),
        ("Regulatory Environment", "What are the key regulations and compliance requirements?", ["regulation", "policy", "compliance", "law"], "news"),
        ("Funding & Investment", "What are the recent funding trends and investor activity?", ["funding", "investment", "venture capital", "startups"], "finance"),
        ("Risks & Challenges", "What are the primary risks and challenges in this space?", ["risks", "challenges", "barriers", "threats"], "general"),
    ]
    return ResearchPlan(
        original_query=query,
        research_plan=[
            SubQuestionPlan(
                sub_question_id=f"sq_{i+1}",
                dimension=dim,
                sub_question=f"{q} — specifically regarding: {query}",
                search_keywords=kw + [query.split()[0]],
                tavily_topic=topic,
            )
            for i, (dim, q, kw, topic) in enumerate(dimensions)
        ],
    )
