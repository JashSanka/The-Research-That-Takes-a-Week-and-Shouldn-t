from groq import AsyncGroq
from app.config import settings
from app.models.schemas import (
    SeniorAnalystOutput, StrategyConsultantOutput,
    RiskOfficerOutput, ConfidenceMetrics,
)

client = None
if settings.GROQ_API_KEY:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

REASONING_SYSTEM = """You are a Chief Risk Officer auditing an AI-generated research report.
Write exactly 2 to 3 sentences explaining why the confidence score was assigned.
Be specific: mention source credibility, data freshness, and whether contradictions were found.
Be direct and professional. No fluff.
Return ONLY the plain text reasoning — no JSON, no bullet points, no headers."""


async def assess(
    senior_outputs: list[SeniorAnalystOutput],
    strategy: StrategyConsultantOutput,
) -> RiskOfficerOutput:
    """
    Agent 4 — Risk Officer.
    Calculates quantified confidence metrics from data; calls Groq only for the reasoning text.
    """

    # ── Aggregate all source evaluations across all sub-questions ──────────────
    all_evals = [e for so in senior_outputs for e in so.source_evaluations]
    total_sources = len(all_evals)

    # 1. Average Source Credibility
    avg_credibility = (
        sum(e.credibility_score for e in all_evals) / total_sources
        if total_sources else 0.0
    )

    # 2. Data Freshness Index
    freshness_index = (
        (sum(e.recency_score for e in all_evals) / (total_sources * 10)) * 100
        if total_sources else 0.0
    )

    # 3. Agreement Factor
    total_facts = sum(len(so.source_evaluations) for so in senior_outputs)
    verified_facts = sum(len(so.verified_key_facts) for so in senior_outputs)
    agreement_factor = verified_facts / total_facts if total_facts else 0.0

    # 4. Contradiction count
    contradiction_count = sum(len(so.contradictions) for so in senior_outputs)

    # 5. Final Confidence Score — Weighted additive formula (0–10)
    #    Credibility: 50% weight  (most important signal)
    #    Agreement:   30% weight  (how consistent are the sources)
    #    Freshness:   20% weight  (how recent is the data)
    if total_sources > 0:
        credibility_component = (avg_credibility / 10.0) * 5.0   # 0–5
        agreement_component   = agreement_factor * 3.0            # 0–3
        freshness_component   = (freshness_index / 100.0) * 2.0  # 0–2
        raw_score = credibility_component + agreement_component + freshness_component
        confidence_score = round(min(max(raw_score, 0.0), 10.0), 1)
    else:
        confidence_score = 0.0

    # 6. Labels
    if confidence_score >= 8.0:
        confidence_label = "High"
        report_reliability = "Ready for Decision"
    elif confidence_score >= 5.0:
        confidence_label = "Moderate"
        report_reliability = "Review Recommended"
    else:
        confidence_label = "Low"
        report_reliability = "Use with Caution"

    # 7. Audit Flags
    audit_flags: list[str] = []

    for so in senior_outputs:
        if len(so.sources) < 3:
            audit_flags.append(
                f"Dimension '{so.sub_question_id}' had fewer than 3 sources ({len(so.sources)} found)."
            )
        dim_avg_cred = (
            sum(e.credibility_score for e in so.source_evaluations) / len(so.source_evaluations)
            if so.source_evaluations else 0.0
        )
        if dim_avg_cred < 5.0:
            audit_flags.append(
                f"Dimension '{so.sub_question_id}' has low average credibility ({dim_avg_cred:.1f}/10)."
            )

    if total_facts > 0 and contradiction_count / total_facts > 0.4:
        audit_flags.append(
            f"High contradiction ratio: {contradiction_count} contradictions across {total_facts} facts."
        )

    if freshness_index < 50.0:
        audit_flags.append(
            f"Data freshness index is below 50% ({freshness_index:.1f}%). Sources may be outdated."
        )

    # 8. Confidence Reasoning (single short Groq call)
    reasoning = await _generate_reasoning(
        score=confidence_score,
        label=confidence_label,
        avg_credibility=avg_credibility,
        freshness_index=freshness_index,
        agreement_factor=agreement_factor,
        contradiction_count=contradiction_count,
        verified_facts=verified_facts,
        total_facts=total_facts,
        audit_flags=audit_flags,
    )

    return RiskOfficerOutput(
        confidence_metrics=ConfidenceMetrics(
            average_source_credibility=round(avg_credibility, 2),
            data_freshness_index=round(freshness_index, 2),
            agreement_factor=round(agreement_factor, 3),
            total_sources_evaluated=total_sources,
            total_facts_extracted=total_facts,
            verified_facts_count=verified_facts,
            contradiction_count=contradiction_count,
        ),
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        report_reliability=report_reliability,
        confidence_reasoning=reasoning,
        audit_flags=audit_flags,
    )


async def _generate_reasoning(
    score: float,
    label: str,
    avg_credibility: float,
    freshness_index: float,
    agreement_factor: float,
    contradiction_count: int,
    verified_facts: int,
    total_facts: int,
    audit_flags: list[str],
) -> str:
    """Generates the 2–3 sentence confidence reasoning via Groq."""
    flags_text = "; ".join(audit_flags) if audit_flags else "None"
    user_message = (
        f"Confidence Score: {score}/10 ({label})\n"
        f"Average Source Credibility: {avg_credibility:.2f}/10\n"
        f"Data Freshness Index: {freshness_index:.1f}%\n"
        f"Agreement Factor: {agreement_factor:.2f}\n"
        f"Contradictions Found: {contradiction_count}\n"
        f"Verified Facts: {verified_facts} out of {total_facts}\n"
        f"Audit Flags: {flags_text}"
    )

    if not client:
        return (
            f"The confidence score of {score}/10 ({label}) was calculated from "
            f"an average source credibility of {avg_credibility:.1f}/10, "
            f"a data freshness index of {freshness_index:.0f}%, "
            f"and an agreement factor of {agreement_factor:.2f}."
        )

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": REASONING_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=256,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[RiskOfficer] Reasoning error: {e}")
        return f"Confidence score of {score}/10 ({label}) based on {total_facts} facts extracted with {contradiction_count} contradictions detected."
