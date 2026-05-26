import io
import json

from ai_scientist.agents import ResearchOrchestrator
from ai_scientist.models import MemoryItem, PaperSource, ResearchQuestion, utc_now


def test_research_question_generates_citation_grounded_brief():
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_test",
        text="How can autonomous research agents improve literature review quality and methodology critique?",
        created_at=utc_now(),
    )
    run, brief = orchestrator.run(question, max_papers=5)
    brief.question_id = question.id

    assert run.status == "completed"
    assert [step.name for step in run.steps] == [
        "Memory Context Agent",
        "Search Agent",
        "Relevance Agent",
        "Extraction Agent",
        "Methodology Critique Agent",
        "Synthesis Agent",
        "Memory Agent",
    ]
    assert brief.question_id == question.id
    assert brief.evidence_items
    assert brief.paper_matrix
    assert brief.bibliography
    assert all(item.source_id for item in brief.evidence_items)
    assert all(finding.strip() for finding in brief.key_findings)


def test_brief_distinguishes_evidence_from_next_steps():
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_trust",
        text="What makes research copilots trustworthy for academic workflows?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)

    assert brief.weak_evidence_flags
    assert brief.open_problems
    assert brief.suggested_next_directions
    assert brief.baseline_recommendations
    assert brief.statistical_validation
    assert all(0 <= row.quality_score <= 100 for row in brief.paper_matrix)
    assert "full-text review" in " ".join(brief.suggested_next_directions).lower()


def test_brief_exports_to_markdown_with_methodology_sections():
    from ai_scientist.export import brief_to_markdown

    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_export",
        text="How should AI research platforms evaluate methodology quality?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)
    markdown = brief_to_markdown(brief)

    assert "## Paper Matrix" in markdown
    assert "## Baseline Recommendations" in markdown
    assert "## Statistical Validation" in markdown
    assert "| Source | Score | Method |" in markdown


def test_research_run_uses_relevant_project_memory():
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_memory",
        text="How should methodology critique handle weak baselines in AI research agents?",
        created_at=utc_now(),
    )
    memory = [
        MemoryItem(
            id="mem_baselines",
            kind="gap",
            content="Weak baselines make AI research agent evaluations hard to trust.",
            tags=["methodology", "baselines"],
            created_at=utc_now(),
        ),
        MemoryItem(
            id="mem_unrelated",
            kind="note",
            content="A note about unrelated administrative work.",
            tags=["admin"],
            created_at=utc_now(),
        ),
    ]
    run, brief = orchestrator.run(question, max_papers=4, memory=memory)

    memory_step = run.steps[0]
    assert memory_step.name == "Memory Context Agent"
    assert memory_step.output["memory_ids"] == ["mem_baselines"]
    assert brief.memory_context_used
    assert "Weak baselines" in brief.memory_context_used[0]


def test_experiment_plan_contains_design_pack_and_template():
    from ai_scientist.experiments import create_experiment_plan

    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_experiment",
        text="How can memory-aware research agents improve methodology critique?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)
    plan = create_experiment_plan(
        brief,
        objective="Evaluate whether memory-aware research agents improve methodology critique",
        memory=[
            MemoryItem(
                id="mem_eval",
                kind="gap",
                content="Evaluation should track citation support and weak baseline handling.",
                tags=["evaluation", "baselines"],
                created_at=utc_now(),
            )
        ],
    )

    assert plan.datasets
    assert plan.baselines
    assert plan.metrics
    assert plan.ablations
    assert plan.statistical_validation
    assert "def main" in plan.implementation_template
    assert plan.source_brief_id == brief.id


def test_experiment_plan_exports_to_markdown():
    from ai_scientist.experiments import create_experiment_plan
    from ai_scientist.export import experiment_plan_to_markdown

    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_plan_export",
        text="How should AI research systems test experiment planning quality?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)
    plan = create_experiment_plan(brief)
    markdown = experiment_plan_to_markdown(plan)

    assert "## Datasets" in markdown
    assert "## Baselines" in markdown
    assert "## Implementation Template" in markdown
    assert "```python" in markdown


def test_hypothesis_generation_links_evidence_memory_and_plan():
    from ai_scientist.experiments import create_experiment_plan
    from ai_scientist.hypotheses import generate_hypotheses

    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_hypothesis",
        text="How can research agents generate testable hypotheses from weak evidence flags?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)
    memory = [
        MemoryItem(
            id="mem_hypothesis",
            kind="gap",
            content="Weak evidence flags should become testable hypotheses rather than generic suggestions.",
            tags=["hypothesis", "evidence"],
            created_at=utc_now(),
        )
    ]
    plan = create_experiment_plan(brief, memory=memory)
    hypotheses = generate_hypotheses(brief, memory=memory, experiment_plan=plan, max_hypotheses=3)

    assert hypotheses
    assert all(item.evidence_ids for item in hypotheses)
    assert all(item.experiment_plan_id == plan.id for item in hypotheses)
    assert all(item.next_test for item in hypotheses)
    assert all(0 <= item.novelty_score <= 100 for item in hypotheses)
    assert all(0 <= item.testability_score <= 100 for item in hypotheses)


def test_research_graph_connects_core_artifacts():
    from ai_scientist.experiments import create_experiment_plan
    from ai_scientist.graph import build_research_graph
    from ai_scientist.hypotheses import generate_hypotheses
    from ai_scientist.models import ResearchProject

    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_graph",
        text="How should a research graph connect briefs, evidence, memory, plans, and hypotheses?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)
    brief.question_id = question.id
    question.brief_id = brief.id
    memory = [
        MemoryItem(
            id="mem_graph",
            kind="gap",
            content="Research graphs should expose which evidence and memory produced each hypothesis.",
            tags=["graph"],
            created_at=utc_now(),
        )
    ]
    plan = create_experiment_plan(brief, memory=memory)
    hypotheses = generate_hypotheses(brief, memory=memory, experiment_plan=plan, max_hypotheses=2)
    project = ResearchProject(
        id="project_graph",
        name="Graph Test",
        created_at=utc_now(),
        questions=[question],
        briefs=[brief],
        memory=memory,
        experiment_plans=[plan],
        hypotheses=hypotheses,
    )
    graph = build_research_graph(project)

    kinds = {node.kind for node in graph.nodes}
    relations = {edge.relation for edge in graph.edges}
    assert {"question", "brief", "evidence", "memory", "experiment_plan", "hypothesis"} <= kinds
    assert {"produced", "supports", "cites", "uses", "tests"} <= relations


def test_sqlite_store_persists_projects_across_instances(tmp_path):
    from ai_scientist.models import ResearchProject
    from ai_scientist.storage import SQLiteStore

    db_path = tmp_path / "ai_scientist.db"
    first = SQLiteStore(db_path)
    project = ResearchProject(id="project_persist", name="Persist", created_at=utc_now())
    first.save_project(project)

    second = SQLiteStore(db_path)
    loaded = second.get_project("project_persist")

    assert loaded is not None
    assert loaded.name == "Persist"


def test_pdf_ingestion_creates_chunks_and_sources(tmp_path):
    from ai_scientist.ingestion import chunks_to_paper_sources, ingest_pdf_bytes

    paper = ingest_pdf_bytes(
        project_id="project_pdf",
        filename="methodology.pdf",
        content=b"Methodology critique needs datasets, baselines, metrics, and confidence intervals.",
        storage_dir=tmp_path,
    )
    sources = chunks_to_paper_sources(paper.chunks)

    assert paper.status == "processed"
    assert paper.chunk_count == 1
    assert sources[0].source_type == "pdf"
    assert sources[0].paper_id == paper.id
    assert sources[0].chunk_id == paper.chunks[0].id
    assert sources[0].page_number == 1


def test_research_run_can_use_pdf_chunk_evidence(tmp_path):
    from ai_scientist.ingestion import chunks_to_paper_sources, ingest_pdf_bytes

    paper = ingest_pdf_bytes(
        project_id="project_pdf_run",
        filename="agents.pdf",
        content=b"Autonomous research agents require benchmark datasets, strong baselines, metrics, and statistical validation.",
        storage_dir=tmp_path,
    )
    sources = chunks_to_paper_sources(paper.chunks)
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_pdf",
        text="How should autonomous research agents use benchmark datasets and baselines?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4, extra_sources=sources)
    pdf_evidence = [item for item in brief.evidence_items if item.paper_id == paper.id]

    assert "pdf" in brief.source_modes_used
    assert pdf_evidence
    assert all(item.chunk_id for item in pdf_evidence)
    assert all(item.page_number == 1 for item in pdf_evidence)


def test_openai_provider_falls_back_without_api_key(monkeypatch):
    from ai_scientist.ai_providers import OpenAIProvider

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = OpenAIProvider(model="test-model").synthesize("hello")

    assert result.provider == "deterministic"
    assert result.warnings


def test_sqlite_store_reconstructs_all_project_artifacts(tmp_path):
    from ai_scientist.experiments import create_experiment_plan
    from ai_scientist.hypotheses import generate_hypotheses
    from ai_scientist.ingestion import ingest_pdf_bytes
    from ai_scientist.models import (
        ResearchAnnotation,
        ResearchProject,
        ResearchTask,
        SourceCollection,
    )
    from ai_scientist.storage import SQLiteStore

    db_path = tmp_path / "beta.db"
    store = SQLiteStore(db_path)
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_full",
        text="How should beta research systems persist normalized artifacts?",
        created_at=utc_now(),
    )
    run, brief = orchestrator.run(question, max_papers=4)
    brief.question_id = question.id
    question.agent_run_id = run.id
    question.brief_id = brief.id
    memory = MemoryItem(id="mem_full", kind="gap", content="Normalized persistence needs aggregate reconstruction.", created_at=utc_now())
    plan = create_experiment_plan(brief, memory=[memory])
    hypotheses = generate_hypotheses(brief, memory=[memory], experiment_plan=plan, max_hypotheses=1)
    paper = ingest_pdf_bytes(
        project_id="project_full",
        filename="storage.pdf",
        content=b"SQLite persistence should keep chunks and ingestion runs.",
        storage_dir=tmp_path,
    )
    project = ResearchProject(
        id="project_full",
        name="Full Beta",
        created_at=utc_now(),
        questions=[question],
        briefs=[brief],
        memory=[memory],
        source_collections=[
            SourceCollection(id="collection_full", name="Sources", source_ids=[paper.id], created_at=utc_now())
        ],
        annotations=[
            ResearchAnnotation(id="ann_full", target_type="brief", target_id=brief.id, note="Looks useful.", created_at=utc_now())
        ],
        experiment_plans=[plan],
        tasks=[
            ResearchTask(id="task_full", kind="experiment_plan", status="completed", title="Plan", summary="Done", created_at=utc_now())
        ],
        hypotheses=hypotheses,
        uploaded_papers=[paper],
        agent_runs=[run],
    )
    store.save_project(project)

    loaded = SQLiteStore(db_path).get_project("project_full")

    assert loaded is not None
    assert loaded.questions[0].id == question.id
    assert loaded.briefs[0].id == brief.id
    assert loaded.memory[0].id == memory.id
    assert loaded.source_collections[0].id == "collection_full"
    assert loaded.annotations[0].id == "ann_full"
    assert loaded.experiment_plans[0].id == plan.id
    assert loaded.tasks[0].id == "task_full"
    assert loaded.hypotheses[0].experiment_plan_id == plan.id
    assert loaded.uploaded_papers[0].chunks[0].paper_id == paper.id
    assert loaded.uploaded_papers[0].ingestion_runs[0].paper_id == paper.id
    assert loaded.agent_runs[0].id == run.id


def test_sqlite_store_normalizes_legacy_project_payload(tmp_path):
    import json
    import sqlite3

    from ai_scientist.models import ResearchProject
    from ai_scientist.storage import SQLiteStore

    db_path = tmp_path / "legacy.db"
    store = SQLiteStore(db_path)
    project = ResearchProject(
        id="project_legacy",
        name="Legacy",
        created_at=utc_now(),
        memory=[MemoryItem(id="mem_legacy", kind="note", content="Loaded from payload.", created_at=utc_now())],
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute("delete from projects")
        conn.execute("delete from memory")
        conn.execute(
            "insert into projects (id, name, description, created_at, payload) values (?, ?, ?, ?, ?)",
            (project.id, project.name, project.description, project.created_at, json.dumps(project.model_dump(mode="json"))),
        )

    loaded = store.get_project("project_legacy")

    assert loaded is not None
    assert loaded.memory[0].id == "mem_legacy"
    with sqlite3.connect(db_path) as conn:
        normalized_count = conn.execute("select count(*) from memory where project_id = ?", (project.id,)).fetchone()[0]
    assert normalized_count == 1


def test_openai_provider_failure_with_api_key_falls_back(monkeypatch):
    from ai_scientist.ai_providers import OpenAIProvider

    def fail(*args, **kwargs):
        raise OSError("network unavailable")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("urllib.request.urlopen", fail)

    result = OpenAIProvider(model="test-model").synthesize("hello")

    assert result.provider == "deterministic"
    assert "OpenAI provider failed" in result.warnings[0]


def test_openalex_search_returns_papers(monkeypatch):
    from ai_scientist.retrieval import SearchService

    def mock_openalex(*args, **kwargs):
        body = json.dumps({
            "results": [{
                "id": "https://openalex.org/W123",
                "title": "OpenAlex Test Paper",
                "abstract_inverted_index": {"Test": [0], "abstract": [1]},
                "authorships": [{"author": {"display_name": "Alice Smith"}}],
                "publication_year": 2023,
                "doi": "https://doi.org/10.1234/test",
                "cited_by_count": 5,
                "open_access": {"oa_url": "https://openalex.org/W123/pdf"},
                "concepts": [{"display_name": "Machine Learning"}],
                "primary_location": {"source": {"display_name": "Test Journal"}},
            }]
        }).encode("utf-8")
        return io.BytesIO(body)

    monkeypatch.setenv("AI_SCIENTIST_LIVE_SEARCH", "1")
    monkeypatch.setattr("urllib.request.urlopen", mock_openalex)
    service = SearchService()
    papers = service._search_openalex("test query", max_papers=3)
    assert len(papers) == 1
    assert papers[0].source_type == "openalex"
    assert papers[0].title == "OpenAlex Test Paper"
    assert papers[0].authors == ["Alice Smith"]
    assert papers[0].doi == "10.1234/test"
    assert papers[0].citation_count == 5
    assert papers[0].concepts == ["Machine Learning"]
    assert papers[0].publisher == "Test Journal"


def test_core_search_requires_api_key(monkeypatch):
    from ai_scientist.retrieval import SearchService

    monkeypatch.delenv("CORE_API_KEY", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_LIVE_SEARCH", "1")
    service = SearchService()
    papers = service._search_core("test query", max_papers=3)
    assert papers == []


def test_core_search_returns_papers(monkeypatch):
    from ai_scientist.retrieval import SearchService

    def mock_core(*args, **kwargs):
        body = json.dumps({
            "results": [{
                "id": 456,
                "title": "CORE Test Paper",
                "abstract": "A test abstract from CORE.",
                "authors": [{"name": "Bob Jones"}],
                "yearOfPublication": 2022,
                "doi": "10.5678/core-test",
                "publisher": "CORE Publisher",
                "sourceUrl": "https://core.ac.uk/456",
            }]
        }).encode("utf-8")
        return io.BytesIO(body)

    monkeypatch.setenv("AI_SCIENTIST_LIVE_SEARCH", "1")
    monkeypatch.setenv("CORE_API_KEY", "test-core-key")
    monkeypatch.setattr("urllib.request.urlopen", mock_core)
    service = SearchService()
    papers = service._search_core("test query", max_papers=3)
    assert len(papers) == 1
    assert papers[0].source_type == "core"
    assert papers[0].title == "CORE Test Paper"
    assert papers[0].doi == "10.5678/core-test"
    assert papers[0].publisher == "CORE Publisher"


def test_crossref_search_returns_papers(monkeypatch):
    from ai_scientist.retrieval import SearchService

    def mock_crossref(*args, **kwargs):
        body = json.dumps({
            "message": {
                "items": [{
                    "title": ["CrossRef Test Paper"],
                    "abstract": "<jats:p>A crossref abstract.</jats:p>",
                    "author": [{"given": "Carol", "family": "Lee"}],
                    "published-print": {"date-parts": [[2021]]},
                    "DOI": "10.9101/cr-test",
                    "publisher": "CrossRef Pub",
                    "container-title": ["Test Journal"],
                }]
            }
        }).encode("utf-8")
        return io.BytesIO(body)

    monkeypatch.setenv("AI_SCIENTIST_LIVE_SEARCH", "1")
    monkeypatch.setattr("urllib.request.urlopen", mock_crossref)
    service = SearchService()
    papers = service._search_crossref("test query", max_papers=3)
    assert len(papers) == 1
    assert papers[0].source_type == "crossref"
    assert papers[0].title == "CrossRef Test Paper"
    assert papers[0].doi == "10.9101/cr-test"
    assert papers[0].publisher == "CrossRef Pub"
    assert papers[0].journal == "Test Journal"


def test_search_service_respects_sources_filter(monkeypatch):
    from ai_scientist.retrieval import SearchService

    def mock_urlopen(*args, **kwargs):
        body = json.dumps({"results": []}).encode("utf-8")
        return io.BytesIO(body)

    monkeypatch.setenv("AI_SCIENTIST_LIVE_SEARCH", "1")
    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    service = SearchService()
    service._search_arxiv = lambda q, max_papers: [PaperSource(id="arxiv_1", title="A", abstract="", url="", source="arxiv", source_type="arxiv", citation="A")]
    service._search_openalex = lambda q, max_papers: [PaperSource(id="openalex_1", title="B", abstract="", url="", source="openalex", source_type="openalex", citation="B")]
    service._search_crossref = lambda q, max_papers: []
    papers_openalex = service.search("test", max_papers=10, sources=["openalex"])
    assert any(p.source_type == "openalex" for p in papers_openalex)
    assert not any(p.source_type == "arxiv" for p in papers_openalex)


def test_tavily_web_search_returns_results(monkeypatch):
    from ai_scientist.agents import tavily_web_search

    def mock_tavily(*args, **kwargs):
        body = json.dumps({
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "content": "Content one"},
                {"title": "Result 2", "url": "https://example.com/2", "content": "Content two"},
            ]
        }).encode("utf-8")
        return io.BytesIO(body)

    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setattr("urllib.request.urlopen", mock_tavily)
    results = tavily_web_search("test query")
    assert len(results) == 2
    assert results[0]["source"] == "tavily"
    assert results[0]["title"] == "Result 1"


def test_tavily_web_search_skipped_without_key(monkeypatch):
    from ai_scientist.agents import tavily_web_search

    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    results = tavily_web_search("test query")
    assert results == []


def test_parse_with_unstructured_returns_pages(monkeypatch):
    from ai_scientist.ingestion import parse_with_unstructured

    def mock_unstructured(*args, **kwargs):
        body = json.dumps([
            {"text": "Page one content", "metadata": {"page_number": 1}},
            {"text": "Page two content", "metadata": {"page_number": 2}},
        ]).encode("utf-8")
        return io.BytesIO(body)

    monkeypatch.setenv("UNSTRUCTURED_API_KEY", "test-unstructured-key")
    monkeypatch.setattr("urllib.request.urlopen", mock_unstructured)
    pages = parse_with_unstructured(b"fake pdf content", "test.pdf")
    assert pages is not None
    assert len(pages) == 2
    assert pages[0] == (1, "Page one content")
    assert pages[1] == (2, "Page two content")


def test_parse_with_unstructured_returns_none_without_key(monkeypatch):
    from ai_scientist.ingestion import parse_with_unstructured

    monkeypatch.delenv("UNSTRUCTURED_API_KEY", raising=False)
    pages = parse_with_unstructured(b"fake pdf content", "test.pdf")
    assert pages is None


def test_parse_with_unstructured_falls_back_on_error(monkeypatch):
    from ai_scientist.ingestion import parse_with_unstructured

    def fail(*args, **kwargs):
        raise OSError("network error")

    monkeypatch.setenv("UNSTRUCTURED_API_KEY", "test-key")
    monkeypatch.setattr("urllib.request.urlopen", fail)
    pages = parse_with_unstructured(b"fake pdf content", "test.pdf")
    assert pages is None


def test_password_gate_blocks_and_login_allows_access(monkeypatch, tmp_path):
    import importlib

    monkeypatch.setenv("AI_SCIENTIST_APP_PASSWORD", "secret")
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "auth.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main

    importlib.reload(config)
    main = importlib.reload(main)

    assert asgi_request(main.app, "GET", "/api/health")["status"] == 200
    assert asgi_request(main.app, "GET", "/login")["status"] == 200
    assert asgi_request(main.app, "GET", "/api/projects")["status"] == 401

    login = asgi_request(
        main.app,
        "POST",
        "/api/login",
        body=b"password=secret",
        headers=[(b"content-type", b"application/x-www-form-urlencoded")],
    )
    cookie = next(value for name, value in login["headers"] if name.lower() == b"set-cookie").split(b";", 1)[0]

    assert login["status"] == 303
    assert asgi_request(main.app, "GET", "/api/projects", headers=[(b"cookie", cookie)])["status"] == 200


def test_api_multipart_upload_and_run_persist_agent_trace(monkeypatch, tmp_path):
    import json
    import importlib

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main
    from ai_scientist.storage import SQLiteStore

    importlib.reload(config)
    main = importlib.reload(main)

    project_response = asgi_request(
        main.app,
        "POST",
        "/api/projects",
        body=json.dumps({"name": "API Beta", "description": ""}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    project = json.loads(project_response["body"])
    boundary = "beta-boundary"
    upload_body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="agents.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
        "Agents need datasets, metrics, baselines, and validation.\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    upload = asgi_request(
        main.app,
        "POST",
        f"/api/projects/{project['id']}/papers/upload",
        body=upload_body,
        headers=[(b"content-type", f"multipart/form-data; boundary={boundary}".encode("utf-8"))],
    )
    run = asgi_request(
        main.app,
        "POST",
        f"/api/projects/{project['id']}/questions/run",
        body=json.dumps(
            {"question": "How should agents use baselines and datasets?", "max_papers": 4, "use_memory": True}
        ).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )

    assert upload["status"] == 200
    assert json.loads(upload["body"])["chunk_count"] == 1
    assert run["status"] == 200
    run_body = json.loads(run["body"])
    assert run_body["run"]["id"]
    stored_runs = SQLiteStore(tmp_path / "api.db").list_agent_runs(project["id"])
    assert stored_runs[0].id == run_body["run"]["id"]


def test_docker_compose_config_exposes_app_and_persistent_volumes():
    compose = open("docker-compose.yml", encoding="utf-8").read()

    assert "8000:8000" in compose
    assert "env_file:" in compose
    assert "./data:/app/data" in compose
    assert "./storage:/app/storage" in compose
    assert "redis:" in compose
    assert "worker:" in compose
    assert "scheduler:" in compose


def test_pdf_ingestion_produces_structured_research_extractions(tmp_path):
    from ai_scientist.ingestion import ingest_pdf_bytes

    paper = ingest_pdf_bytes(
        project_id="project_extract",
        filename="rigor.pdf",
        content=(
            b"Our method uses a transformer framework for research triage. "
            b"The dataset contains benchmark papers and annotated data. "
            b"Evaluation reports accuracy metrics against a baseline comparison. "
            b"A limitation is sensitivity to corpus coverage. Future work should extend validation. "
            b"The approach assumes reliable source extraction."
        ),
        storage_dir=tmp_path,
    )

    assert paper.extractions.claims
    assert paper.extractions.methods
    assert paper.extractions.datasets
    assert paper.extractions.metrics
    assert paper.extractions.baselines
    assert paper.extractions.limitations
    assert paper.extractions.future_work
    assert paper.extractions.assumptions
    assert all(item.chunk_id for item in paper.extractions.all_items())
    assert all(item.page_number == 1 for item in paper.extractions.all_items())


def test_brief_quality_report_flags_methodology_gaps():
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_quality",
        text="How should research assistants report weak methodology evidence?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)

    assert brief.quality_report_id
    assert brief.quality_report is not None
    assert 0 <= brief.quality_report.citation_coverage <= 1
    assert brief.quality_report.missing_baselines or brief.quality_report.weak_methodology_signals
    assert brief.unsupported_claims == brief.quality_report.unsupported_claims
    assert brief.memory_used == []


def test_quality_report_marks_empty_evidence_as_insufficient():
    from ai_scientist.intelligence import build_quality_report

    report = build_quality_report("brief_empty", [], [])

    assert report.insufficient_evidence is True
    assert report.speculative_conclusions
    assert "insufficient" in report.summary.lower()


def test_v12_hybrid_retrieval_surfaces_scores_and_sources():
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="test-hybrid",
        text="How do retrieval-augmented generation systems compare to fine-tuned models for biomedical relation extraction?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)
    assert brief.evidence_items
    assert any(item.retrieval_method in {"semantic", "hybrid"} for item in brief.evidence_items)
    assert all(item.semantic_score is not None for item in brief.evidence_items)
    assert brief.quality_report is not None
    assert brief.quality_report.embedding_coverage == 1
    assert brief.quality_report.connectors_used


def test_sqlite_persists_quality_reports_and_extraction_artifact_rows(tmp_path):
    import sqlite3

    from ai_scientist.ingestion import ingest_pdf_bytes
    from ai_scientist.models import ResearchProject
    from ai_scientist.storage import SQLiteStore

    store = SQLiteStore(tmp_path / "v11.db")
    paper = ingest_pdf_bytes(
        project_id="project_v11",
        filename="paper.pdf",
        content=b"The method uses a benchmark dataset, baseline comparison, metric evaluation, limitation, and future work.",
        storage_dir=tmp_path,
    )
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(id="question_v11", text="How should methodology evidence be stored?", created_at=utc_now())
    _, brief = orchestrator.run(question, max_papers=4)
    project = ResearchProject(id="project_v11", name="V1.1", created_at=utc_now(), briefs=[brief], uploaded_papers=[paper])
    store.save_project(project)

    loaded = SQLiteStore(tmp_path / "v11.db").get_project("project_v11")
    with sqlite3.connect(tmp_path / "v11.db") as conn:
        artifact_count = conn.execute("select count(*) from extracted_artifacts where project_id = ?", ("project_v11",)).fetchone()[0]
        report_count = conn.execute("select count(*) from quality_reports where project_id = ?", ("project_v11",)).fetchone()[0]

    assert loaded.uploaded_papers[0].extractions.all_items()
    assert loaded.briefs[0].quality_report is not None
    assert artifact_count > 0
    assert report_count == 1


def test_memory_promote_endpoint_deduplicates_items(monkeypatch, tmp_path):
    import json
    import importlib

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "promote.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main

    importlib.reload(config)
    main = importlib.reload(main)
    project = json.loads(
        asgi_request(
            main.app,
            "POST",
            "/api/projects",
            body=json.dumps({"name": "Memory Promote", "description": ""}).encode("utf-8"),
            headers=[(b"content-type", b"application/json")],
        )["body"]
    )
    payload = {"kind": "baseline", "content": "Compare against a simple baseline.", "source_ids": ["ev1"], "tags": ["quality"]}

    first = asgi_request(
        main.app,
        "POST",
        f"/api/projects/{project['id']}/memory/promote",
        body=json.dumps(payload).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    second = asgi_request(
        main.app,
        "POST",
        f"/api/projects/{project['id']}/memory/promote",
        body=json.dumps({**payload, "source_ids": ["ev2"]}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )

    memory = json.loads(second["body"])["memory"]
    assert first["status"] == 200
    assert second["status"] == 200
    assert len([item for item in memory if item["content"] == payload["content"]]) == 1
    assert sorted(memory[0]["source_ids"]) == ["ev1", "ev2"]


def test_research_graph_includes_v11_artifact_relationships(tmp_path):
    from ai_scientist.graph import build_research_graph
    from ai_scientist.ingestion import ingest_pdf_bytes
    from ai_scientist.models import ResearchProject

    paper = ingest_pdf_bytes(
        project_id="project_graph_v11",
        filename="graph.pdf",
        content=b"The method uses a dataset and metric evaluation. A limitation remains and the approach assumes clean data.",
        storage_dir=tmp_path,
    )
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(id="question_graph_v11", text="How do graph relations expose research rigor?", created_at=utc_now())
    _, brief = orchestrator.run(question, max_papers=4)
    project = ResearchProject(id="project_graph_v11", name="Graph V1.1", created_at=utc_now(), briefs=[brief], uploaded_papers=[paper])
    graph = build_research_graph(project)

    relations = {edge.relation for edge in graph.edges}
    kinds = {node.kind for node in graph.nodes}

    assert {"quality_report", "method", "dataset", "metric", "limitation", "assumption"} & kinds
    assert {"quality_checks", "uses", "evaluated_by", "has_limitation", "has_assumption"} & relations


def test_sqlite_store_persists_jobs_and_object_records(tmp_path):
    from ai_scientist.models import JobRecord, ObjectStorageRecord
    from ai_scientist.storage import SQLiteStore

    store = SQLiteStore(tmp_path / "ops.db")
    job = JobRecord(id="job_ops", project_id="project_ops", kind="pdf_ingestion", created_at=utc_now(), updated_at=utc_now())
    obj = ObjectStorageRecord(
        id="obj_ops",
        project_id="project_ops",
        name="paper.pdf",
        kind="pdf",
        backend="local",
        uri=str(tmp_path / "paper.pdf"),
        content_type="application/pdf",
        size_bytes=10,
        created_at=utc_now(),
    )

    store.save_job(job)
    store.save_object_record(obj)

    assert store.get_job("job_ops").kind == "pdf_ingestion"
    assert store.list_jobs("project_ops")[0].id == "job_ops"
    assert store.get_object_record("obj_ops").name == "paper.pdf"
    assert store.list_object_records("project_ops")[0].id == "obj_ops"


def test_v1_job_and_artifact_endpoints(monkeypatch, tmp_path):
    import importlib
    import json

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DISABLE_AUTH", "1")
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "ops_api.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main

    importlib.reload(config)
    main = importlib.reload(main)
    project = json.loads(
        asgi_request(
            main.app,
            "POST",
            "/api/v1/projects",
            body=json.dumps({"name": "Ops API", "description": ""}).encode("utf-8"),
            headers=[(b"content-type", b"application/json")],
        )["body"]
    )
    upload = asgi_request(
        main.app,
        "POST",
        f"/api/projects/{project['id']}/papers/upload?filename=ops.pdf",
        body=b"Methodology critique requires datasets, baselines, and metrics.",
        headers=[(b"content-type", b"application/pdf")],
    )
    artifacts = json.loads(asgi_request(main.app, "GET", f"/api/v1/projects/{project['id']}/artifacts")["body"])
    jobs = json.loads(
        asgi_request(
            main.app,
            "POST",
            "/api/v1/jobs",
            body=json.dumps({"project_id": project["id"], "kind": "export_generation", "payload": {}}).encode("utf-8"),
            headers=[(b"content-type", b"application/json")],
        )["body"]
    )
    job_status = json.loads(asgi_request(main.app, "GET", f"/api/v1/jobs/{jobs['id']}")["body"])

    assert upload["status"] == 200
    assert artifacts[0]["kind"] == "pdf"
    assert job_status["kind"] == "export_generation"


def test_production_readiness_rejects_unsafe_defaults(monkeypatch):
    import pytest

    import ai_scientist.main as main

    monkeypatch.setattr(main.settings, "environment", "production")
    monkeypatch.setattr(main.settings, "store_backend", "postgres")
    monkeypatch.setattr(main.settings, "database_url", "postgresql://user:pass@localhost/db")
    monkeypatch.setattr(main.settings, "app_password", "change-me")
    monkeypatch.setattr(main.settings, "jwt_secret", "dev-change-me")
    monkeypatch.setattr(main.settings, "cookie_secure", False)
    monkeypatch.setattr(main.settings, "storage_backend", "local")

    with pytest.raises(RuntimeError):
        main.validate_production_configuration()


def asgi_request(app, method, path, body=b"", headers=None):
    import anyio

    async def call():
        sent = []
        query = b""
        request_path = path
        if "?" in path:
            request_path, query_text = path.split("?", 1)
            query = query_text.encode("ascii")
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": request_path,
            "raw_path": request_path.encode("ascii"),
            "query_string": query,
            "headers": headers or [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "root_path": "",
            "path_params": {},
        }
        received = False

        async def receive():
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            sent.append(message)

        await app(scope, receive, send)
        start = next(message for message in sent if message["type"] == "http.response.start")
        chunks = [message.get("body", b"") for message in sent if message["type"] == "http.response.body"]
        return {"status": start["status"], "headers": start["headers"], "body": b"".join(chunks).decode("utf-8")}

    return anyio.run(call)
