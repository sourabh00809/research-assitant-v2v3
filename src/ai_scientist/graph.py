from __future__ import annotations

from .models import ResearchGraph, ResearchGraphEdge, ResearchGraphNode, ResearchProject


def build_research_graph(project: ResearchProject) -> ResearchGraph:
    nodes: dict[str, ResearchGraphNode] = {}
    edges: list[ResearchGraphEdge] = []

    def add_node(node: ResearchGraphNode) -> None:
        nodes[node.id] = node

    for question in project.questions:
        add_node(ResearchGraphNode(id=question.id, label=question.text[:80], kind="question", summary=question.text))
        if question.brief_id:
            edges.append(ResearchGraphEdge(source=question.id, target=question.brief_id, relation="produced"))

    for brief in project.briefs:
        add_node(ResearchGraphNode(id=brief.id, label=brief.title[:80], kind="brief", summary=brief.question_interpretation))
        if brief.quality_report_id:
            add_node(
                ResearchGraphNode(
                    id=brief.quality_report_id,
                    label="Brief quality report",
                    kind="quality_report",
                    summary=(brief.quality_report.summary if brief.quality_report else "Evidence quality report."),
                )
            )
            edges.append(ResearchGraphEdge(source=brief.quality_report_id, target=brief.id, relation="quality_checks"))
        for evidence in brief.evidence_items[:20]:
            add_node(
                ResearchGraphNode(
                    id=evidence.id,
                    label=f"{evidence.extraction_type}: {evidence.claim[:55]}",
                    kind="evidence",
                    summary=evidence.support,
                )
            )
            source_id = f"source_{evidence.source_id}"
            add_node(ResearchGraphNode(id=source_id, label=evidence.source_id, kind="source", summary="Retrieved or seed source."))
            edges.append(ResearchGraphEdge(source=brief.id, target=evidence.id, relation="supports"))
            edges.append(ResearchGraphEdge(source=evidence.id, target=source_id, relation="cites"))
            if evidence.extraction_type == "claim":
                for problem in brief.open_problems[:3]:
                    gap_id = f"gap_{brief.id}_{abs(hash(problem))}"
                    add_node(ResearchGraphNode(id=gap_id, label=problem[:80], kind="gap", summary=problem))
                    edges.append(ResearchGraphEdge(source=evidence.id, target=gap_id, relation="suggests"))

    for item in project.memory:
        add_node(ResearchGraphNode(id=item.id, label=f"{item.kind}: {item.content[:60]}", kind="memory", summary=item.content))
        for source_id in item.source_ids:
            edges.append(ResearchGraphEdge(source=item.id, target=f"source_{source_id}", relation="cites"))

    for plan in project.experiment_plans:
        add_node(ResearchGraphNode(id=plan.id, label=plan.title[:80], kind="experiment_plan", summary=plan.objective))
        if plan.source_brief_id:
            edges.append(ResearchGraphEdge(source=plan.source_brief_id, target=plan.id, relation="produced"))
        for memory_ref in plan.memory_used:
            memory_id = extract_bracket_id(memory_ref)
            if memory_id:
                edges.append(ResearchGraphEdge(source=plan.id, target=memory_id, relation="uses"))

    for hypothesis in project.hypotheses:
        add_node(ResearchGraphNode(id=hypothesis.id, label=hypothesis.title[:80], kind="hypothesis", summary=hypothesis.statement))
        for evidence_id in hypothesis.evidence_ids:
            edges.append(ResearchGraphEdge(source=hypothesis.id, target=evidence_id, relation="uses"))
        for memory_id in hypothesis.memory_ids:
            edges.append(ResearchGraphEdge(source=hypothesis.id, target=memory_id, relation="uses"))
        if hypothesis.experiment_plan_id:
            edges.append(ResearchGraphEdge(source=hypothesis.experiment_plan_id, target=hypothesis.id, relation="tests"))

    for paper in project.uploaded_papers:
        paper_node_id = f"source_{paper.id}"
        add_node(ResearchGraphNode(id=paper_node_id, label=paper.title[:80], kind="source", summary=paper.filename))
        for artifact in paper.extractions.all_items()[:40]:
            add_node(
                ResearchGraphNode(
                    id=artifact.id,
                    label=f"{artifact.kind}: {artifact.text[:70]}",
                    kind=artifact.kind,
                    summary=artifact.supporting_text,
                )
            )
            if artifact.kind == "claim":
                edges.append(ResearchGraphEdge(source=paper_node_id, target=artifact.id, relation="supports"))
            elif artifact.kind == "method":
                edges.append(ResearchGraphEdge(source=artifact.id, target=paper_node_id, relation="cites"))
            elif artifact.kind == "dataset":
                for method in paper.extractions.methods[:4]:
                    edges.append(ResearchGraphEdge(source=method.id, target=artifact.id, relation="uses"))
            elif artifact.kind == "metric":
                for method in paper.extractions.methods[:4]:
                    edges.append(ResearchGraphEdge(source=method.id, target=artifact.id, relation="evaluated_by"))
            elif artifact.kind == "limitation":
                edges.append(ResearchGraphEdge(source=paper_node_id, target=artifact.id, relation="has_limitation"))
            elif artifact.kind == "assumption":
                edges.append(ResearchGraphEdge(source=paper_node_id, target=artifact.id, relation="has_assumption"))
            else:
                edges.append(ResearchGraphEdge(source=artifact.id, target=paper_node_id, relation="cites"))

    return ResearchGraph(nodes=list(nodes.values()), edges=dedupe_edges(edges))


def extract_bracket_id(value: str) -> str:
    if "[" not in value or "]" not in value:
        return ""
    return value.rsplit("[", 1)[-1].split("]", 1)[0]


def dedupe_edges(edges: list[ResearchGraphEdge]) -> list[ResearchGraphEdge]:
    seen: set[tuple[str, str, str]] = set()
    result: list[ResearchGraphEdge] = []
    for edge in edges:
        key = (edge.source, edge.target, edge.relation)
        if key in seen:
            continue
        seen.add(key)
        result.append(edge)
    return result
