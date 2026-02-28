from fastapi import APIRouter, HTTPException
from app.models.schemas import ResearchQuery
from app.services.pipeline import run_pipeline

router = APIRouter()


@router.post("/query", response_model=dict)
async def process_query(body: ResearchQuery):
    """
    Runs the full 4-agent research pipeline:
    1. Junior Analyst  — query decomposition into sub-questions
    2. Senior Analyst  — per-sub-question Tavily retrieval + critical evaluation
    3. Scoring Engine  — recency + cross-reference enrichment
    4. Strategy Consultant — structured intelligence synthesis
    5. Risk Officer    — quantified confidence scoring
    """
    try:
        result = await run_pipeline(body.query)
        return {"status": "success", "report": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
