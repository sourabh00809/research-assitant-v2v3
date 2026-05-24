from ai_scientist.agents import ResearchOrchestrator
from ai_scientist.models import MemoryItem, ResearchQuestion, utc_now


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
    assert all("[" in finding and "]" in finding for finding in brief.key_findings)


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
<<<<<<< HEAD
    assert "postgres:" in compose
    assert "redis:" in compose
    assert "minio:" in compose
    assert "worker:" in compose
    assert "scheduler:" in compose
=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44


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


<<<<<<< HEAD
def test_v12_hybrid_retrieval_surfaces_scores_and_sources():
    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(
        id="question_v12_scores",
        text="How can retrieval augmented research agents improve evidence quality?",
        created_at=utc_now(),
    )
    _, brief = orchestrator.run(question, max_papers=4)

    assert brief.evidence_items
    assert any(item.retrieval_method in {"semantic", "hybrid"} for item in brief.evidence_items)
    assert all(item.semantic_score is not None for item in brief.evidence_items)
    assert brief.quality_report is not None
    assert brief.quality_report.embedding_coverage == 1
    assert brief.quality_report.connectors_used


def test_v12_deduplicates_sources_and_merges_badges():
    from ai_scientist.models import PaperSource
    from ai_scientist.retrieval import dedupe_papers

    arxiv = PaperSource(
        id="arxiv_dup",
        title="Shared Retrieval Paper",
        abstract="Retrieval improves evidence quality.",
        url="https://arxiv.org/abs/1234.5678",
        source="arxiv",
        source_type="arxiv",
        sources=["arxiv"],
        citation="A. Author (2024), Shared Retrieval Paper.",
        arxiv_id="1234.5678",
    )
    semantic = PaperSource(
        id="s2_dup",
        title="Shared Retrieval Paper",
        abstract="Retrieval improves evidence quality with richer metadata.",
        url="https://semanticscholar.org/paper/test",
        source="semantic_scholar",
        source_type="semantic_scholar",
        sources=["semantic_scholar"],
        citation="A. Author (2024), Shared Retrieval Paper.",
        arxiv_id="1234.5678",
        citation_count=42,
    )

    deduped = dedupe_papers([arxiv, semantic])

    assert len(deduped) == 1
    assert deduped[0].sources == ["arxiv", "semantic_scholar"]
    assert deduped[0].citation_count == 42


def test_v12_semantic_chunk_ranking_handles_paraphrase(tmp_path):
    from ai_scientist.embeddings import rank_chunks
    from ai_scientist.ingestion import ingest_pdf_bytes

    paper = ingest_pdf_bytes(
        project_id="project_chunk_rank",
        filename="chunks.pdf",
        content=(
            b"Methods: autonomous research agents evaluate benchmark datasets and baseline comparisons. "
            b"Conclusion: administrative notes about scheduling are unrelated."
        ),
        storage_dir=tmp_path,
    )

    ranked = rank_chunks("academic copilots compare evaluation data", paper.chunks)

    assert ranked
    assert ranked[0].semantic_score > 0
    assert ranked[0].final_score > 0


def test_v12_connector_and_embedding_status_endpoints(monkeypatch, tmp_path):
    import importlib
    import json

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "v12_api.db"))
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
            body=json.dumps({"name": "V12", "description": ""}).encode("utf-8"),
            headers=[(b"content-type", b"application/json")],
        )["body"]
    )
    upload = asgi_request(
        main.app,
        "POST",
        f"/api/projects/{project['id']}/papers/upload?filename=test.pdf",
        body=b"Evaluation methods require benchmark datasets and baselines.",
        headers=[(b"content-type", b"application/pdf")],
    )
    connectors = asgi_request(main.app, "GET", "/api/connectors/status")
    status = asgi_request(main.app, "GET", f"/api/projects/{project['id']}/embedding-status")

    assert upload["status"] == 200
    assert connectors["status"] == 200
    assert {item["source_type"] for item in json.loads(connectors["body"])} == {"arxiv", "semantic_scholar", "pubmed"}
    assert json.loads(status["body"])["embedded"] == 1


def test_v13_image_classification_recommends_cifar_and_resnet():
    from ai_scientist.experiment import recommend_experiment_plan

    recommendation = recommend_experiment_plan(
        None,
        question="Design an image classification experiment for robust vision models",
    )

    dataset_names = " ".join(item["name"] for item in recommendation["datasets"])
    baseline_names = " ".join(item["name"] for item in recommendation["baselines"])
    assert "CIFAR-10" in dataset_names
    assert "ResNet" in baseline_names
    assert recommendation["template_id"] == "image_classification"


def test_v13_literature_extractions_rank_above_template_defaults():
    from ai_scientist.experiment import recommend_experiment_plan
    from ai_scientist.models import EvidenceItem, ResearchBrief

    brief = ResearchBrief(
        id="brief_reco",
        question_id="question_reco",
        title="Research Brief: image classification",
        question_interpretation="Test",
        key_findings=[],
        evidence_items=[
            EvidenceItem(
                id="ev_dataset",
                source_id="source",
                claim="Custom Pavement Crack Dataset",
                support="Custom Pavement Crack Dataset",
                confidence="medium",
                extraction_type="dataset",
            ),
            EvidenceItem(
                id="ev_baseline",
                source_id="source",
                claim="ResNet-50 baseline",
                support="ResNet-50 baseline",
                confidence="medium",
                extraction_type="baseline",
            ),
        ],
        paper_matrix=[],
        methodology_assessment=[],
        weak_evidence_flags=[],
        open_problems=[],
        suggested_next_directions=[],
        bibliography=[],
        created_at=utc_now(),
    )

    recommendation = recommend_experiment_plan(brief, question="image classification")

    assert recommendation["datasets"][0]["name"] == "Custom Pavement Crack Dataset"
    assert recommendation["baselines"][0]["name"] == "ResNet-50 baseline"


def test_v13_generated_script_compiles(tmp_path):
    import py_compile
    from ai_scientist.experiments import create_experiment_plan

    orchestrator = ResearchOrchestrator()
    question = ResearchQuestion(id="question_v13_script", text="How should RAG evidence quality be evaluated?", created_at=utc_now())
    _, brief = orchestrator.run(question, max_papers=4)
    plan = create_experiment_plan(brief)
    path = tmp_path / "generated_experiment.py"
    path.write_text(plan.generated_script, encoding="utf-8")

    py_compile.compile(str(path), doraise=True)
    assert "bootstrap_ci" in plan.generated_script
    assert "paired_t_test" in plan.generated_script


def test_v14_exports_and_sse_run_events(monkeypatch, tmp_path):
    import importlib
    import json

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "v14.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main

    importlib.reload(config)
    main = importlib.reload(main)
    project = json.loads(asgi_request(main.app, "POST", "/api/projects", body=b'{"name":"V14"}', headers=[(b"content-type", b"application/json")])["body"])
    run_response = asgi_request(
        main.app,
        "POST",
        f"/api/projects/{project['id']}/questions/run",
        body=b'{"question":"How should evidence graphs support research?","max_papers":4}',
        headers=[(b"content-type", b"application/json")],
    )
    body = json.loads(run_response["body"])

    assert asgi_request(main.app, "GET", "/app")["status"] == 200
    assert asgi_request(main.app, "GET", f"/api/projects/{project['id']}/graph/export.json")["status"] == 200
    assert asgi_request(main.app, "GET", f"/api/projects/{project['id']}/graph/export.svg")["status"] == 200
    assert asgi_request(main.app, "GET", f"/api/projects/{project['id']}/runs/{body['run']['id']}/events")["status"] == 200


def test_v2_migration_and_subscription_helpers(tmp_path):
    from ai_scientist.migrate import sqlite_to_postgres_summary
    from ai_scientist.saas import create_single_user_tenant, stripe_webhook_stub, usage_allowed
    from ai_scientist.storage import SQLiteStore
    from ai_scientist.models import ResearchProject

    db_path = tmp_path / "migrate.db"
    SQLiteStore(db_path).save_project(ResearchProject(id="project_migrate", name="Migrate", created_at=utc_now()))
    summary = sqlite_to_postgres_summary(db_path, "postgresql://user:pass@localhost/db", dry_run=True)
    user, team, subscription = create_single_user_tenant()
    subscription = stripe_webhook_stub({"type": "invoice.payment_failed"}, subscription)

    assert summary["table_counts"]["projects"] == 1
    assert user.role == "owner"
    assert team.name
    assert subscription.status == "past_due"
    assert usage_allowed(subscription, [], "agent_runs") is True


def test_v3_agent_audit_and_sandbox(monkeypatch, tmp_path):
    import importlib
    import json
    from ai_scientist.sandbox import run_python_sandbox

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "v3.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main

    importlib.reload(config)
    main = importlib.reload(main)
    created = asgi_request(
        main.app,
        "POST",
        "/api/v1/agents?project_id=project_demo",
        body=b'{"type":"literature_monitor","name":"Weekly monitor","goal":"Find new RAG papers","schedule":"weekly"}',
        headers=[(b"content-type", b"application/json")],
    )
    project = json.loads(created["body"])
    run_id = project["autonomous_agent_runs"][0]["id"]
    audit = asgi_request(main.app, "GET", f"/api/v1/agent-runs/{run_id}/audit?project_id=project_demo")
    sandbox = run_python_sandbox("print('ok')", timeout_seconds=3)

    assert created["status"] == 200
    assert audit["status"] == 200
    assert sandbox["exit_code"] == 0
    assert sandbox["network_disabled"] is True


def test_v2_tenancy_usage_endpoints_persist_limits(monkeypatch, tmp_path):
    import importlib
    import json

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "v2_platform.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main

    importlib.reload(config)
    main = importlib.reload(main)
    tenant = json.loads(
        asgi_request(
            main.app,
            "POST",
            "/api/v1/tenancy/bootstrap",
            body=b'{"email":"owner@example.com","team_name":"Research Lab","tier":"pro"}',
            headers=[(b"content-type", b"application/json")],
        )["body"]
    )
    usage = asgi_request(
        main.app,
        "POST",
        "/api/v1/usage",
        body=json.dumps({"subject_id": tenant["team"]["id"], "kind": "agent_runs", "quantity": 2}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    limits = json.loads(
        asgi_request(
            main.app,
            "GET",
            f"/api/v1/usage/limits?subject_id={tenant['team']['id']}&team_id={tenant['team']['id']}",
        )["body"]
    )

    assert tenant["subscription"]["tier"] == "pro"
    assert usage["status"] == 200
    assert limits["usage"]["agent_runs"] == 2
    assert limits["allowed"]["agent_runs"] is True


def test_v2_signup_login_billing_jobs_and_health(monkeypatch, tmp_path):
    import importlib
    import json

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "v2_full.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main

    importlib.reload(config)
    main = importlib.reload(main)
    signup = asgi_request(
        main.app,
        "POST",
        "/api/v1/auth/signup",
        body=b'{"email":"full@example.com","password":"password123","team_name":"Full Stack Lab"}',
        headers=[(b"content-type", b"application/json")],
    )
    cookie = next(value for name, value in signup["headers"] if name.lower() == b"set-cookie").split(b";", 1)[0]
    session = json.loads(asgi_request(main.app, "GET", "/api/v1/auth/session", headers=[(b"cookie", cookie)])["body"])
    checkout = asgi_request(
        main.app,
        "POST",
        "/api/v1/billing/checkout",
        body=json.dumps({"team_id": session["team"]["id"], "tier": "pro"}).encode("utf-8"),
        headers=[(b"content-type", b"application/json")],
    )
    job = asgi_request(
        main.app,
        "POST",
        "/api/v1/jobs",
        body=b'{"kind":"agent_workflow","payload":{"agent":"monitor"}}',
        headers=[(b"content-type", b"application/json")],
    )
    health = json.loads(asgi_request(main.app, "GET", "/api/v1/admin/health")["body"])

    assert signup["status"] == 200
    assert session["authenticated"] is True
    assert json.loads(checkout["body"])["provider"] == "stripe-test-stub"
    assert json.loads(job["body"])["status"] == "queued"
    assert "database" in health
    assert "redis_workers" in health


def test_v3_literature_monitor_step_persists_search_notification_and_audit(monkeypatch, tmp_path):
    import importlib
    import json

    monkeypatch.delenv("AI_SCIENTIST_APP_PASSWORD", raising=False)
    monkeypatch.setenv("AI_SCIENTIST_DB_PATH", str(tmp_path / "v3_workflow.db"))
    monkeypatch.setenv("AI_SCIENTIST_STORAGE_DIR", str(tmp_path / "storage"))
    import ai_scientist.config as config
    import ai_scientist.main as main
    from ai_scientist.storage import SQLiteStore

    importlib.reload(config)
    main = importlib.reload(main)
    project = json.loads(asgi_request(main.app, "POST", "/api/projects", body=b'{"name":"Agents"}', headers=[(b"content-type", b"application/json")])["body"])
    created = json.loads(
        asgi_request(
            main.app,
            "POST",
            f"/api/v1/projects/{project['id']}/agents",
            body=b'{"type":"literature_monitor","name":"Monitor","goal":"Find new agent papers","schedule":"weekly"}',
            headers=[(b"content-type", b"application/json")],
        )["body"]
    )
    run_id = created["autonomous_agent_runs"][0]["id"]
    stepped = json.loads(
        asgi_request(
            main.app,
            "POST",
            f"/api/v1/agent-runs/{run_id}/step?project_id={project['id']}",
            body=b'{"query":"retrieval augmented research agents"}',
            headers=[(b"content-type", b"application/json")],
        )["body"]
    )
    loaded = SQLiteStore(tmp_path / "v3_workflow.db").get_project(project["id"])

    assert stepped["autonomous_agent_runs"][0]["status"] == "completed"
    assert stepped["saved_searches"][0]["query"] == "retrieval augmented research agents"
    assert stepped["notifications"]
    assert loaded is not None
    assert loaded.autonomous_agent_runs[0].decisions


=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
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


<<<<<<< HEAD
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


=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
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
