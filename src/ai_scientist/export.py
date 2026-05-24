from __future__ import annotations

from .models import ExperimentPlan, ResearchBrief


def brief_to_markdown(brief: ResearchBrief) -> str:
    sections = [
        f"# {brief.title}",
        f"Created: {brief.created_at}",
        "## Question Interpretation",
        brief.question_interpretation,
        list_section("Key Findings", brief.key_findings),
        list_section("Methodology Assessment", brief.methodology_assessment),
        list_section("Weak Evidence Flags", brief.weak_evidence_flags),
        list_section("Baseline Recommendations", brief.baseline_recommendations),
        list_section("Statistical Validation", brief.statistical_validation),
        list_section("Memory Context Used", brief.memory_context_used),
        retrieval_quality_section(brief),
        list_section("Open Problems", brief.open_problems),
        list_section("Suggested Next Directions", brief.suggested_next_directions),
        matrix_section(brief),
        evidence_section(brief),
        list_section("Bibliography", brief.bibliography),
    ]
    return "\n\n".join(section for section in sections if section).strip() + "\n"


def list_section(title: str, items: list[str]) -> str:
    if not items:
        return ""
    body = "\n".join(f"- {format_item(item)}" for item in items)
    return f"## {title}\n{body}"


def matrix_section(brief: ResearchBrief) -> str:
    if not brief.paper_matrix:
        return ""
    rows = [
        "| Source | Score | Method | Dataset | Metrics | Baselines | Validation | Limitations |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in brief.paper_matrix:
        rows.append(
            "| "
            + " | ".join(
                clean_cell(value)
                for value in [
                    row.source_id,
                    str(row.quality_score),
                    row.method,
                    row.dataset,
                    row.metrics,
                    row.baselines,
                    row.validation,
                    row.limitations,
                ]
            )
            + " |"
        )
    return "## Paper Matrix\n" + "\n".join(rows)


def evidence_section(brief: ResearchBrief) -> str:
    if not brief.evidence_items:
        return ""
    lines = ["## Evidence"]
    for item in brief.evidence_items:
        scores = []
        if item.semantic_score is not None:
            scores.append(f"semantic={item.semantic_score:.2f}")
        if item.keyword_score is not None:
            scores.append(f"keyword={item.keyword_score:.2f}")
        suffix = f" [{item.retrieval_method}; {', '.join(scores)}]" if scores else f" [{item.retrieval_method}]"
        lines.append(f"- [{item.source_id}] {item.extraction_type} ({item.confidence}){suffix}: {item.claim}")
    return "\n".join(lines)


def retrieval_quality_section(brief: ResearchBrief) -> str:
    report = brief.quality_report
    if not report:
        return ""
    return "\n".join(
        [
            "## Retrieval Quality",
            f"- Semantic hits: {report.semantic_hits}",
            f"- Keyword-only hits: {report.keyword_hits}",
            f"- Hybrid hits: {report.hybrid_hits}",
            f"- Embedding coverage: {round(report.embedding_coverage * 100)}%",
            f"- Connectors used: {', '.join(report.connectors_used) if report.connectors_used else 'none'}",
        ]
    )


def clean_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def experiment_plan_to_markdown(plan: ExperimentPlan) -> str:
    sections = [
        f"# {plan.title}",
        f"Created: {plan.created_at}",
        "## Objective",
        plan.objective,
        "## Hypothesis",
        plan.hypothesis,
        list_section("Datasets", plan.datasets),
        list_section("Baselines", plan.baselines),
        list_section("Metrics", plan.metrics),
        list_section("Ablations", plan.ablations or plan.ablation_config.variables),
        list_section("Statistical Validation", plan.statistical_validation or [plan.validation_plan.strategy]),
        list_section("Risks", plan.risks),
        list_section("Memory Used", plan.memory_used),
        "## Implementation Template",
        f"```python\n{(plan.generated_script or plan.implementation_template).strip()}\n```",
    ]
    return "\n\n".join(section for section in sections if section).strip() + "\n"


def format_item(item) -> str:
    if isinstance(item, str):
        return item
    if hasattr(item, "model_dump"):
        data = item.model_dump()
        name = data.pop("name", "")
        details = ", ".join(f"{key}={value}" for key, value in data.items() if value not in ("", [], None))
        return f"{name} ({details})" if details else name
    return str(item)
