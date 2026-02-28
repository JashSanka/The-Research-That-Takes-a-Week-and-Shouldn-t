import asyncio
from tavily import AsyncTavilyClient
from app.config import settings
from app.models.schemas import SourceItem, SubQuestionPlan

tavily_client = None
if settings.TAVILY_API_KEY:
    tavily_client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)


async def retrieve_for_subquestion(sq: SubQuestionPlan, max_results: int = 5) -> list[SourceItem]:
    """
    Retrieves sources for a single SubQuestionPlan using:
    - sq.search_keywords joined as the query string
    - sq.tavily_topic as the Tavily topic ("general" | "news" | "finance")

    This replaces the old retrieve_sources() function and enables domain-targeted
    search without manual .gov/.edu string detection.
    """
    query = " ".join(sq.search_keywords)

    if not tavily_client:
        print(f"Warning: TAVILY_API_KEY not set. Returning mock data for: {sq.sub_question_id}")
        return [
            SourceItem(
                title=f"Mock Source — {sq.dimension}",
                url=f"https://example.com/{sq.sub_question_id}",
                published_date="2025-09-01T00:00:00Z",
                snippet=f"Mocked snippet for sub-question: {sq.sub_question}",
            )
        ]

    # Map topic to freshness window:
    # news   → 30 days  (breaking/recent news)
    # finance → 90 days (recent financial data)
    # general → 180 days (background research)
    days_map = {"news": 30, "finance": 90, "general": 180}
    days = days_map.get(sq.tavily_topic, 90)

    try:
        response = await tavily_client.search(
            query=query,
            topic=sq.tavily_topic,      # Tavily native domain targeting
            search_depth="advanced",
            include_answer=False,
            include_raw_content=False,
            max_results=max_results,
            include_images=False,
            days=days,                  # Real-time: restrict to recent content
        )
        sources = []
        for result in response.get("results", []):
            sources.append(SourceItem(
                title=result.get("title", "Unknown Title"),
                url=result.get("url", ""),
                published_date=result.get("published_date", None),
                snippet=result.get("content", "No content available."),
            ))
        return sources
    except Exception as e:
        print(f"[Retriever] Error fetching sources for {sq.sub_question_id}: {e}")
        return []


# ── Legacy helpers kept for backward compat ────────────────────────────────────

async def retrieve_sources(query: str, max_results: int = 5) -> list[SourceItem]:
    """Legacy single-query retrieval (kept for backward compat)."""
    if not tavily_client:
        return [
            SourceItem(
                title=f"Mock Source for {query}",
                url="https://example.com/mock-source",
                published_date="2026-01-01T00:00:00Z",
                snippet=f"This is a mocked snippet for: {query}",
            )
        ]
    try:
        response = await tavily_client.search(
            query=query,
            search_depth="advanced",
            include_answer=False,
            include_raw_content=False,
            max_results=max_results,
            include_images=False,
            days=90,                    # Real-time: last 90 days
        )
        return [
            SourceItem(
                title=r.get("title", "Unknown Title"),
                url=r.get("url", ""),
                published_date=r.get("published_date", None),
                snippet=r.get("content", "No content available."),
            )
            for r in response.get("results", [])
        ]
    except Exception as e:
        print(f"Error fetching sources from Tavily: {e}")
        return []


async def retrieve_all_sources(sub_questions: list[str]) -> list[SourceItem]:
    """Legacy helper — retrieve sources for plain string sub-questions."""
    tasks = [retrieve_sources(sq, max_results=3) for sq in sub_questions]
    results = await asyncio.gather(*tasks)

    all_sources: list[SourceItem] = []
    seen_urls: set[str] = set()
    for source_list in results:
        for source in source_list:
            if source.url not in seen_urls:
                all_sources.append(source)
                seen_urls.add(source.url)
    return all_sources
