from app.models.schemas import SourceItem
from app.utils.helpers import clamp


def calculate_confidence_score(sources: list[SourceItem], freshness_index: float) -> float:
    """
    Calculates the final confidence score (1–10).

    Formula: Avg Credibility × Agreement Factor × Freshness Factor

    - Agreement Factor: 0.9 if 4+ sources (richer evidence), else 0.8
    - Freshness Factor: scales from 0.7 (0% fresh) to 1.0 (100% fresh)
    """
    if not sources:
        return 0.0

    avg_credibility = sum(s.score or 5.0 for s in sources) / len(sources)
    agreement_factor = 0.9 if len(sources) >= 4 else 0.8
    freshness_factor = 0.7 + (freshness_index / 100.0) * 0.3

    raw_score = avg_credibility * agreement_factor * freshness_factor
    return round(clamp(raw_score, 1.0, 10.0), 2)
