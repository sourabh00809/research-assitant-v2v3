from __future__ import annotations

from .experiment.planner import create_structured_experiment_plan
from .models import ExperimentPlan, MemoryItem, ResearchBrief


def create_experiment_plan(
    brief: ResearchBrief,
    objective: str | None = None,
    memory: list[MemoryItem] | None = None,
    hypothesis_id: str | None = None,
    template_id: str | None = None,
    status: str = "draft",
) -> ExperimentPlan:
    return create_structured_experiment_plan(
        brief=brief,
        objective=objective,
        memory=memory,
        hypothesis_id=hypothesis_id,
        template_id=template_id,
        status=status,
    )
