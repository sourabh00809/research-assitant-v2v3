from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..graph import build_research_graph
from ..models import ResearchGraph
from ._helpers import escape_xml
from ._state import STORE

router = APIRouter(tags=["graph"])


@router.get("/api/projects/{project_id}/graph", response_model=ResearchGraph)
def get_graph(project_id: str) -> ResearchGraph:
    project = STORE.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return build_research_graph(project)


@router.get("/api/projects/{project_id}/graph/export.json")
def export_graph_json(project_id: str) -> dict:
    graph = get_graph(project_id)
    return graph.model_dump(mode="json")


@router.get("/api/projects/{project_id}/graph/export.svg", response_class=PlainTextResponse)
def export_graph_svg(project_id: str) -> PlainTextResponse:
    graph = get_graph(project_id)
    rows = []
    for index, node in enumerate(graph.nodes[:80]):
        y = 30 + index * 24
        rows.append(f'<text x="20" y="{y}" font-size="12">{escape_xml(node.kind)}: {escape_xml(node.label[:80])}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{max(120, 60 + len(rows) * 24)}">{"".join(rows)}</svg>'
    return PlainTextResponse(svg, media_type="image/svg+xml")
