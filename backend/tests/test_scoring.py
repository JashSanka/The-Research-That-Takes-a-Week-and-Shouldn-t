import pytest
from app.models.schemas import SourceItem
from app.services.scoring import calculate_freshness_index, calculate_credibility_score, calculate_confidence_score

def test_calculate_credibility_score():
    score = calculate_credibility_score("https://nytimes.com/article", "Test", "Test snippet")
    assert score > 7.0
    
    score2 = calculate_credibility_score("https://blogspot.com/post", "Test", "Test snippet")
    assert score2 < 5.0

def test_calculate_freshness_index():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    
    # 10 days old
    date1 = (now - timedelta(days=10)).isoformat().replace("+00:00", "Z")
    # 200 days old
    date2 = (now - timedelta(days=200)).isoformat().replace("+00:00", "Z")
    
    sources = [
        SourceItem(title="A", url="a", snippet="a", published_date=date1),
        SourceItem(title="B", url="b", snippet="b", published_date=date2),
    ]
    
    index = calculate_freshness_index(sources)
    assert 50.0 < index < 100.0

def test_calculate_confidence_score():
    sources = [
        SourceItem(title="A", url="a", snippet="a", score=8.0),
        SourceItem(title="B", url="b", snippet="b", score=7.0),
    ]
    freshness = 90.0
    
    conf = calculate_confidence_score(sources, freshness)
    assert 5.0 < conf < 10.0
