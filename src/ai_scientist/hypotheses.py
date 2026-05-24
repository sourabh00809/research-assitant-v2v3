from __future__ import annotations

from .models import ExperimentPlan, HypothesisCandidate, MemoryItem, ResearchBrief, new_id, utc_now


def generate_hypotheses(
    brief: ResearchBrief,
    memory: list[MemoryItem],
    experiment_plan: ExperimentPlan | None = None,
    max_hypotheses: int = 4,
) -> list[HypothesisCandidate]:
    candidates: list[HypothesisCandidate] = []
    evidence_ids = [item.id for item in brief.evidence_items[:4]]
    gap_memory = [item for item in memory if item.status == "active" and item.kind in {"gap", "rejected_direction", "idea"}]

    seed_items = brief.open_problems[:2] + brief.weak_evidence_flags[:2] + [item.content for item in gap_memory[:2]]
    if not seed_items:
        seed_items = brief.suggested_next_directions[:2]

    for index, seed in enumerate(seed_items[:max_hypotheses], start=1):
        memory_ids = [item.id for item in gap_memory if overlap(seed, item.content)][:3]
        title = f"Hypothesis {index}: {shorten(seed, 72)}"
        statement = build_statement(seed, experiment_plan)
        candidates.append(
            HypothesisCandidate(
                id=new_id("hyp"),
                title=title,
                statement=statement,
                rationale=(
                    "Generated from cited evidence, methodology weaknesses, project memory, "
                    "and the latest experiment plan when available."
                ),
                evidence_ids=evidence_ids,
                memory_ids=memory_ids,
                experiment_plan_id=experiment_plan.id if experiment_plan else None,
                novelty_score=score_novelty(seed, memory_ids),
                testability_score=score_testability(seed, experiment_plan),
                risk_flags=build_risks(seed, brief),
                next_test=build_next_test(seed, experiment_plan),
                created_at=utc_now(),
            )
        )
    return candidates


def build_statement(seed: str, plan: ExperimentPlan | None) -> str:
    if plan:
        return (
            f"If the system directly addresses '{seed}', then {plan.hypothesis.lower()} "
            "under the plan's datasets, baselines, metrics, and ablations."
        )
    return f"If a research workflow directly addresses '{seed}', then it should improve evidence support and methodology quality versus generic assistance."


def build_next_test(seed: str, plan: ExperimentPlan | None) -> str:
    if plan:
        metric = plan.metrics[0] if plan.metrics else "primary metric"
        baseline = plan.baselines[0] if plan.baselines else "strong baseline"
        return f"Run the latest experiment plan against {baseline} and compare on {metric}."
    return "Create an experiment plan with explicit datasets, baselines, metrics, and uncertainty reporting."


def build_risks(seed: str, brief: ResearchBrief) -> list[str]:
    risks = []
    if "not explicit" in seed.lower() or "full text" in seed.lower():
        risks.append("May be an artifact of abstract-only extraction; validate against full text.")
    if brief.weak_evidence_flags:
        risks.append("Depends on weakly reported methodology in one or more sources.")
    risks.append("Novelty must be checked against the broader literature before prioritization.")
    return risks[:3]


def score_novelty(seed: str, memory_ids: list[str]) -> int:
    score = 65
    if "gap" in seed.lower() or "not explicit" in seed.lower():
        score += 10
    if memory_ids:
        score += 5
    return min(score, 95)


def score_testability(seed: str, plan: ExperimentPlan | None) -> int:
    score = 50
    if plan:
        score += 30
    if any(term in seed.lower() for term in ["dataset", "metric", "baseline", "validation", "score"]):
        score += 10
    return min(score, 95)


def overlap(left: str, right: str) -> bool:
    left_terms = {term for term in left.lower().split() if len(term) > 4}
    right_terms = {term for term in right.lower().split() if len(term) > 4}
    return bool(left_terms & right_terms)


def shorten(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."
