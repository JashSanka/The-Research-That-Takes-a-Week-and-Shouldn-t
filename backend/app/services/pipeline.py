"""
Pipeline Orchestrator — ties all 4 agents together.

Flow:
  Agent 1 (Junior Analyst)      → ResearchPlan (5–7 sub-questions)
  Tavily retrieval (concurrent) → sources per sub-question
  Agent 2 (Senior Analyst ×N)   → SeniorAnalystOutput per sub-question (concurrent)
  Scoring Engine                → enriches recency + cross-ref scores
  Agent 3 (Strategy Consultant) → StrategyConsultantOutput
  Agent 4 (Risk Officer)        → RiskOfficerOutput
"""
import asyncio
from app.models.schemas import AgenticResearchReport
from app.agents import junior_analyst, senior_analyst, strategy_consultant, risk_officer
from app.services import scoring_engine
from app.services.retriever import retrieve_for_subquestion


async def run_pipeline(query: str) -> AgenticResearchReport:
    # ── Step 1: Agent 1 — Junior Analyst ──────────────────────────────────────
    print(f"[Pipeline] Step 1: Decomposing query...")
    plan = await junior_analyst.decompose(query)

    # ── Step 2: Parallel Tavily retrieval per sub-question ────────────────────
    print(f"[Pipeline] Step 2: Retrieving sources for {len(plan.research_plan)} sub-questions...")
    retrieved = await asyncio.gather(*[
        retrieve_for_subquestion(sq) for sq in plan.research_plan
    ])

    # ── Step 3: Agent 2 — Senior Analyst (concurrent per sub-question) ────────
    print(f"[Pipeline] Step 3: Senior Analyst evaluating {len(plan.research_plan)} dimensions...")
    senior_outputs = await asyncio.gather(*[
        senior_analyst.evaluate(sq, sources)
        for sq, sources in zip(plan.research_plan, retrieved)
    ])
    senior_outputs = list(senior_outputs)

    # ── Scoring Engine: enrich with recency + cross-ref points ────────────────
    senior_outputs = scoring_engine.enrich_evaluations(senior_outputs)

    # ── Step 4: Agent 3 — Strategy Consultant ─────────────────────────────────
    print(f"[Pipeline] Step 4: Strategy Consultant synthesizing report...")
    strategy = await strategy_consultant.synthesize(query, senior_outputs)

    # ── Step 5: Agent 4 — Risk Officer ────────────────────────────────────────
    print(f"[Pipeline] Step 5: Risk Officer calculating confidence...")
    risk = await risk_officer.assess(senior_outputs, strategy)

    print(f"[Pipeline] Complete. Confidence: {risk.confidence_score}/10 ({risk.confidence_label})")

    return AgenticResearchReport(
        query=query,
        research_plan=plan,
        senior_analysis=senior_outputs,
        strategy_report=strategy,
        risk_assessment=risk,
    )
