from datetime import datetime, timezone
from app.models.schemas import SourceItem
from app.utils.helpers import clamp

REPUTABLE_DOMAINS = [
    "nytimes.com", "reuters.com", "bloomberg.com", "wsj.com",
    "nature.com", "arxiv.org", "forbes.com", "mckinsey.com", "gartner.com"
]
SKETCHY_DOMAINS = ["blogspot.com", "wordpress.com"]


def calculate_credibility_score(url: str, title: str, snippet: str) -> float:
    """
    Scores a source's credibility based on domain type and content signals.
    Returns a score between 1.0 and 10.0.
    """
    score = 5.0

    if any(tld in url for tld in [".gov", ".edu", ".org"]):
        score += 2.0

    if any(domain in url for domain in REPUTABLE_DOMAINS):
        score += 2.5

    if any(domain in url for domain in SKETCHY_DOMAINS):
        score -= 1.5

    # Small deterministic variance from snippet length
    score += (len(snippet) % 10) * 0.1

    return clamp(score, 1.0, 10.0)


def calculate_freshness_index(sources: list[SourceItem]) -> float:
    """
    Calculates a freshness index (0–100) based on source publication dates.
    """
    if not sources:
        return 0.0

    now = datetime.now(timezone.utc)
    total = 0.0
    count = 0

    for source in sources:
        if not source.published_date:
            continue
        try:
            date_str = source.published_date.replace("Z", "+00:00")
            pub_date = datetime.fromisoformat(date_str)
            days_old = (now - pub_date).days

            if days_old <= 30:
                freshness = 100.0
            elif days_old <= 365:
                freshness = 100.0 - ((days_old - 30) / 335) * 50.0
            elif days_old <= 1825:
                freshness = 50.0 - ((days_old - 365) / 1460) * 40.0
            else:
                freshness = max(0.0, 10.0 - ((days_old - 1825) / 1825) * 10.0)

            total += freshness
            count += 1
        except Exception:
            pass

    return total / count if count > 0 else 50.0


def score_sources_pipeline(sources: list[SourceItem]) -> tuple[list[SourceItem], float]:
    """
    Runs the full credibility scoring pipeline.
    Returns: (scored_and_sorted_sources, freshness_index)
    """
    for source in sources:
        source.score = calculate_credibility_score(source.url, source.title, source.snippet)

    freshness_index = calculate_freshness_index(sources)

    # Sort highest credibility first
    sources.sort(key=lambda x: x.score or 0.0, reverse=True)

    return sources, freshness_index
