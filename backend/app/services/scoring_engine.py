"""
Scoring Engine — Rule-based recency and cross-reference scoring.
Domain quality is handled upstream by Tavily topic targeting.
"""
from datetime import datetime, timezone
from app.models.schemas import SourceEvaluation, SeniorAnalystOutput


MAJOR_MEDIA = {
    "reuters.com", "bloomberg.com", "nytimes.com", "wsj.com",
    "ft.com", "economist.com", "bbc.com", "bbc.co.uk",
    "forbes.com", "techcrunch.com", "wired.com", "theguardian.com",
    "washingtonpost.com", "apnews.com", "cnbc.com", "cnn.com",
}


def compute_recency_points(published_date: str | None) -> int:
    """
    Returns 0–3 points based on how recent the publication date is.
      < 6 months  → 3
      < 1 year    → 2
      < 2 years   → 1
      >= 2 years  → 0
      No date     → 0
    """
    if not published_date:
        return 0
    try:
        date_str = published_date.replace("Z", "+00:00")
        pub_date = datetime.fromisoformat(date_str)
        now = datetime.now(timezone.utc)
        days_old = (now - pub_date).days

        if days_old < 180:
            return 3
        elif days_old < 365:
            return 2
        elif days_old < 730:
            return 1
        else:
            return 0
    except Exception:
        return 0


def compute_cross_ref_points(url: str, all_sub_source_urls: list[list[str]]) -> int:
    """
    Returns +2 if this URL appears in sources for 2 or more sub-questions.
    """
    appearances = sum(1 for url_list in all_sub_source_urls if url in url_list)
    return 2 if appearances >= 2 else 0


def enrich_evaluations(
    senior_outputs: list[SeniorAnalystOutput],
) -> list[SeniorAnalystOutput]:
    """
    Enriches each SourceEvaluation with recency_points and cross_ref_score
    by looking at all sources across all sub-questions.
    """
    # Build a list of URL sets per sub-question for cross-ref lookup
    all_sub_source_urls: list[list[str]] = [
        [e.url for e in so.source_evaluations]
        for so in senior_outputs
    ]

    # Match evaluations to their source's published_date
    url_to_date: dict[str, str | None] = {}
    for so in senior_outputs:
        for src in so.sources:
            url_to_date[src.url] = src.published_date

    enriched: list[SeniorAnalystOutput] = []
    for so in senior_outputs:
        new_evals: list[SourceEvaluation] = []
        for e in so.source_evaluations:
            pub_date = url_to_date.get(e.url)
            e.recency_points = compute_recency_points(pub_date)
            e.cross_ref_score = compute_cross_ref_points(e.url, all_sub_source_urls)
            new_evals.append(e)

        so.source_evaluations = new_evals
        enriched.append(so)

    return enriched
