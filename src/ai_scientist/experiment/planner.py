from __future__ import annotations

from ..agents import select_memory_context
from ..models import AblationConfig, ExperimentPlan, MemoryItem, ResearchBrief, ValidationPlan, new_id, utc_now
from .recommender import recommend
from .scripts import generate_script
from .validation import validation_snippets


def recommend_experiment_plan(
    brief: ResearchBrief | None,
    question: str = "",
    domain: str | None = None,
    task: str | None = None,
    top_k: int = 5,
) -> dict:
    return recommend(brief=brief, question=question, domain=domain, task=task, top_k=top_k)


def create_structured_experiment_plan(
    brief: ResearchBrief,
    objective: str | None = None,
    memory: list[MemoryItem] | None = None,
    hypothesis_id: str | None = None,
    template_id: str | None = None,
    status: str = "draft",
) -> ExperimentPlan:
    recommendation = recommend(brief=brief, question=" ".join([brief.title, objective or ""]), top_k=5)
    if template_id:
        recommendation["template_id"] = template_id
    memory_context = select_memory_context(objective or brief.title, memory or [])
    validation = ValidationPlan(
        strategy=recommendation["validation"],
        confidence_interval="bootstrap",
        statistical_tests=["paired_t_test", "wilcoxon"],
        correction="fdr",
        code_snippets=validation_snippets(["paired_t_test", "wilcoxon"], "bootstrap", "fdr"),
    )
    plan = ExperimentPlan(
        id=new_id("exp"),
        source_question_id=brief.question_id,
        source_brief_id=brief.id,
        hypothesis_id=hypothesis_id,
        title=f"Experiment Plan: {brief.title.replace('Research Brief: ', '')[:80]}",
        description="Domain-specific experiment plan generated from retrieved evidence, gaps, and project memory.",
        objective=objective or f"Test a concrete research direction emerging from {brief.title}.",
        hypothesis=infer_hypothesis(brief, objective),
        domain=recommendation["domain"],
        task=recommendation["task"],
        template_id=recommendation["template_id"],
        datasets=recommendation["datasets"],
        baselines=recommendation["baselines"],
        metrics=recommendation["metrics"],
        ablation_config=AblationConfig(
            variables=recommendation.get("ablation_vars", []),
            conditions=[
                "template_recommended_baseline",
                "strong_literature_baseline",
                "proposed_method",
                "no_retrieval_ablation",
                "no_memory_ablation",
            ],
        ),
        validation_plan=validation,
        status=status,  # type: ignore[arg-type]
        ablations=recommendation.get("ablation_vars", []),
        statistical_validation=[
            validation.strategy,
            f"{validation.confidence_interval} confidence intervals",
            ", ".join(validation.statistical_tests),
            f"{validation.correction} multiple-comparison correction",
        ],
        risks=infer_risks(brief),
        memory_used=[f"{item.kind}: {item.content} [{item.id}]" for item in memory_context],
        created_at=utc_now(),
    )
    plan.generated_script = generate_script(plan)
    plan.implementation_template = plan.generated_script
    return plan


def infer_hypothesis(brief: ResearchBrief, objective: str | None) -> str:
    if objective:
        return f"If {objective.rstrip('.')}, then the proposed workflow should improve primary metrics versus the selected baselines."
    if brief.open_problems:
        return f"Addressing '{brief.open_problems[0]}' will improve evidence quality and methodology rigor versus baseline workflows."
    return "The proposed method will outperform template and literature baselines under the selected validation plan."


def infer_risks(brief: ResearchBrief) -> list[str]:
    return list(dict.fromkeys(brief.weak_evidence_flags[:4] + [
        "External API recommendations may be unavailable; template fallbacks must remain valid.",
        "Generated scripts include placeholders and require user dataset paths before execution.",
        "Statistical conclusions are invalid without enough repeated runs or folds.",
    ]))[:8]
