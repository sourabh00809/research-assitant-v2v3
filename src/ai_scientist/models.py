from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaperSource(BaseModel):
    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str
    url: str
    source: str
    citation: str
    doi: str | None = None
    arxiv_id: str | None = None
    relevance_score: float = 0.0
    relevance_reason: str = ""
    source_type: Literal["pdf", "arxiv", "semantic_scholar", "pubmed", "seed"] = "seed"
    sources: list[str] = Field(default_factory=list)
    citation_count: int | None = None
    influential_citation_count: int | None = None
    open_access_url: str | None = None
    submitted_at: str | None = None
    updated_at: str | None = None
    categories: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    journal: str | None = None
    embedding_status: Literal["pending", "embedded", "failed"] = "pending"
    paper_id: str | None = None
    chunk_id: str | None = None
    page_number: int | None = None


class ExtractionArtifact(BaseModel):
    id: str
    paper_id: str
    source_id: str
    text: str
    supporting_text: str
    confidence: Literal["high", "medium", "low"] = "medium"
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    extraction_method: Literal["deterministic", "openai", "fallback", "manual"] = "deterministic"
    page_number: int | None = None
    chunk_id: str | None = None
    created_at: str


class ExtractedClaim(ExtractionArtifact):
    kind: Literal["claim"] = "claim"


class MethodologyItem(ExtractionArtifact):
    kind: Literal["method"] = "method"


class DatasetMention(ExtractionArtifact):
    kind: Literal["dataset"] = "dataset"


class MetricMention(ExtractionArtifact):
    kind: Literal["metric"] = "metric"


class BaselineMention(ExtractionArtifact):
    kind: Literal["baseline"] = "baseline"


class LimitationItem(ExtractionArtifact):
    kind: Literal["limitation"] = "limitation"


class FutureWorkItem(ExtractionArtifact):
    kind: Literal["future_work"] = "future_work"


class AssumptionItem(ExtractionArtifact):
    kind: Literal["assumption"] = "assumption"


class PaperExtractionSet(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)
    methods: list[MethodologyItem] = Field(default_factory=list)
    datasets: list[DatasetMention] = Field(default_factory=list)
    metrics: list[MetricMention] = Field(default_factory=list)
    baselines: list[BaselineMention] = Field(default_factory=list)
    limitations: list[LimitationItem] = Field(default_factory=list)
    future_work: list[FutureWorkItem] = Field(default_factory=list)
    assumptions: list[AssumptionItem] = Field(default_factory=list)

    def all_items(self) -> list[ExtractionArtifact]:
        return [
            *self.claims,
            *self.methods,
            *self.datasets,
            *self.metrics,
            *self.baselines,
            *self.limitations,
            *self.future_work,
            *self.assumptions,
        ]


class EvidenceItem(BaseModel):
    id: str
    source_id: str
    claim: str
    support: str
    confidence: Literal["high", "medium", "low"]
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    extraction_type: Literal["claim", "method", "dataset", "metric", "baseline", "limitation", "future_work", "assumption"]
    extraction_method: Literal["deterministic", "openai", "fallback", "manual"] = "deterministic"
    source_quote: str = ""
    source_span: str = ""
    paper_id: str | None = None
    chunk_id: str | None = None
    page_number: int | None = None
    semantic_score: float | None = None
    keyword_score: float | None = None
    retrieval_method: Literal["semantic", "keyword", "hybrid"] = "keyword"
    source_type: Literal["pdf", "arxiv", "semantic_scholar", "pubmed", "seed"] | None = None
    source_badges: list[str] = Field(default_factory=list)


class EmbeddingRecord(BaseModel):
    id: str
    artifact_type: Literal["paper", "chunk", "claim", "memory", "question"]
    artifact_id: str
    model: str
    vector: list[float]
    created_at: str


class EmbeddingJob(BaseModel):
    id: str
    artifact_type: Literal["paper", "chunk", "claim", "memory", "question"]
    artifact_id: str
    status: Literal["pending", "running", "completed", "failed"]
    started_at: str | None = None
    completed_at: str | None = None
    error: str = ""
    created_at: str


class ScoredResult(BaseModel):
    artifact_type: Literal["paper", "chunk", "claim", "memory"]
    artifact_id: str
    semantic_score: float
    keyword_score: float = 0.0
    final_score: float


class ChunkRankingResult(BaseModel):
    chunk_id: str
    semantic_score: float
    position_weight: float
    final_score: float
    section_label: Literal["abstract", "introduction", "method", "results", "discussion", "conclusion", "unknown"] = "unknown"


class MemoryRelevanceScore(BaseModel):
    memory_item_id: str
    similarity_score: float
    influence: Literal["confirmed", "contradicted", "extended"] = "extended"


class DeduplicationRecord(BaseModel):
    id: str
    kept_source_id: str
    duplicate_source_id: str
    match_type: Literal["doi", "arxiv_id", "title", "semantic"]
    score: float
    created_at: str


class ConnectorResult(BaseModel):
    source_type: Literal["arxiv", "semantic_scholar", "pubmed"]
    paper_id: str
    title: str
    abstract: str
    authors: list[str] = Field(default_factory=list)
    date: str | None = None
    url: str = ""
    doi: str | None = None
    citation_count: int | None = None
    open_access_url: str | None = None


class ConnectorStatus(BaseModel):
    source_type: Literal["arxiv", "semantic_scholar", "pubmed"]
    enabled: bool
    last_run_at: str | None = None
    last_result_count: int = 0
    health: Literal["ready", "disabled", "degraded"] = "ready"


class PaperComparison(BaseModel):
    source_id: str
    method: str
    dataset: str
    metrics: str
    assumptions: str
    limitations: str
    future_work: str
    baselines: str = "Baselines not explicit in available abstract."
    validation: str = "Validation design not explicit in available abstract."
    quality_score: int = Field(default=0, ge=0, le=100)
    quality_flags: list[str] = Field(default_factory=list)


class AgentStep(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "failed"]
    summary: str
    output: dict[str, Any] = Field(default_factory=dict)


class AgentRun(BaseModel):
    id: str
    question_id: str
    status: Literal["running", "completed", "failed"]
    started_at: str
    completed_at: str | None = None
    model: str = "deterministic-local-orchestrator"
    cost_usd: float = 0.0
    steps: list[AgentStep] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provider: str = "deterministic"


class ResearchBrief(BaseModel):
    id: str
    question_id: str
    title: str
    question_interpretation: str
    key_findings: list[str]
    evidence_items: list[EvidenceItem]
    paper_matrix: list[PaperComparison]
    methodology_assessment: list[str]
    weak_evidence_flags: list[str]
    open_problems: list[str]
    suggested_next_directions: list[str]
    baseline_recommendations: list[str] = Field(default_factory=list)
    statistical_validation: list[str] = Field(default_factory=list)
    memory_context_used: list[str] = Field(default_factory=list)
    source_modes_used: list[str] = Field(default_factory=list)
    provider_used: str = "deterministic"
    provider_summary: str = ""
    quality_report_id: str | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    speculative_suggestions: list[str] = Field(default_factory=list)
    memory_used: list[str] = Field(default_factory=list)
    memory_relevance_scores: list[MemoryRelevanceScore] = Field(default_factory=list)
    quality_report: "EvidenceQualityReport | None" = None
    bibliography: list[str]
    created_at: str


class EvidenceQualityReport(BaseModel):
    id: str
    brief_id: str
    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    unsupported_claims: list[str] = Field(default_factory=list)
    weak_methodology_signals: list[str] = Field(default_factory=list)
    missing_datasets: list[str] = Field(default_factory=list)
    missing_baselines: list[str] = Field(default_factory=list)
    missing_metrics: list[str] = Field(default_factory=list)
    missing_statistical_validation: list[str] = Field(default_factory=list)
    speculative_conclusions: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    semantic_hits: int = 0
    keyword_hits: int = 0
    hybrid_hits: int = 0
    embedding_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    connectors_used: list[str] = Field(default_factory=list)
    summary: str = ""
    created_at: str


class ResearchQuestion(BaseModel):
    id: str
    text: str
    created_at: str
    agent_run_id: str | None = None
    brief_id: str | None = None


class MemoryItem(BaseModel):
    id: str
    kind: Literal[
        "claim",
        "gap",
        "method",
        "dataset",
        "metric",
        "baseline",
        "idea",
        "experiment_idea",
        "hypothesis",
        "rejected_direction",
        "note",
        "user_note",
    ]
    content: str
    source_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: Literal["active", "archived"] = "active"
    created_at: str


class SourceCollection(BaseModel):
    id: str
    name: str
    description: str = ""
    source_ids: list[str] = Field(default_factory=list)
    created_at: str


class ResearchAnnotation(BaseModel):
    id: str
    target_type: Literal["brief", "source", "memory", "question"]
    target_id: str
    note: str
    created_at: str


class ExperimentDataset(BaseModel):
    name: str
    source: str = ""
    url: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""


class ExperimentBaseline(BaseModel):
    name: str
    description: str = ""
    reference: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""


class ExperimentMetric(BaseModel):
    name: str
    formula: str = ""
    higher_is_better: bool = True
    rationale: str = ""


class AblationConfig(BaseModel):
    variables: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    control: str = "strongest_baseline"


class ValidationPlan(BaseModel):
    strategy: str = "5-fold cross-validation"
    confidence_interval: str = "bootstrap"
    statistical_tests: list[str] = Field(default_factory=lambda: ["paired_t_test"])
    correction: str = "fdr"
    code_snippets: dict[str, str] = Field(default_factory=dict)


class ExperimentPlan(BaseModel):
    id: str
    source_question_id: str | None = None
    source_brief_id: str | None = None
    hypothesis_id: str | None = None
    title: str
    description: str = ""
    objective: str
    hypothesis: str
    domain: str = "general"
    task: str = "research_evaluation"
    template_id: str | None = None
    datasets: list[ExperimentDataset | str]
    baselines: list[ExperimentBaseline | str]
    metrics: list[ExperimentMetric | str]
    ablation_config: AblationConfig = Field(default_factory=AblationConfig)
    validation_plan: ValidationPlan = Field(default_factory=ValidationPlan)
    generated_script: str = ""
    status: Literal["draft", "approved", "running", "completed"] = "draft"
    ablations: list[str] = Field(default_factory=list)
    statistical_validation: list[str] = Field(default_factory=list)
    implementation_template: str = ""
    risks: list[str]
    memory_used: list[str] = Field(default_factory=list)
    created_at: str


class ResearchTask(BaseModel):
    id: str
    kind: Literal["literature_review", "experiment_plan", "hypothesis_generation", "monitor"]
    status: Literal["queued", "running", "completed", "failed"]
    title: str
    summary: str
    target_id: str | None = None
    created_at: str
    completed_at: str | None = None


class ResearchGraphNode(BaseModel):
    id: str
    label: str
    kind: Literal[
        "question",
        "brief",
        "source",
        "evidence",
        "memory",
        "experiment_plan",
        "hypothesis",
        "claim",
        "method",
        "dataset",
        "metric",
        "baseline",
        "limitation",
        "future_work",
        "assumption",
        "quality_report",
        "gap",
    ]
    summary: str = ""


class ResearchGraphEdge(BaseModel):
    source: str
    target: str
    relation: Literal[
        "produced",
        "cites",
        "supports",
        "saved_as",
        "uses",
        "proposes",
        "tests",
        "suggests",
        "motivates",
        "evaluated_by",
        "has_limitation",
        "has_assumption",
        "quality_checks",
    ]


class ResearchGraph(BaseModel):
    nodes: list[ResearchGraphNode] = Field(default_factory=list)
    edges: list[ResearchGraphEdge] = Field(default_factory=list)


class HypothesisCandidate(BaseModel):
    id: str
    title: str
    statement: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    experiment_plan_id: str | None = None
    novelty_score: int = Field(default=50, ge=0, le=100)
    testability_score: int = Field(default=50, ge=0, le=100)
    risk_flags: list[str] = Field(default_factory=list)
    next_test: str
    created_at: str


class IngestionRun(BaseModel):
    id: str
    paper_id: str
    status: Literal["completed", "failed"]
    message: str = ""
    pages_extracted: int = 0
    chunks_created: int = 0
    created_at: str


class DocumentChunk(BaseModel):
    id: str
    paper_id: str
    page_number: int
    text: str
    created_at: str


class UploadedPaper(BaseModel):
    id: str
    project_id: str
    title: str
    filename: str
    content_type: str = "application/pdf"
    source_type: Literal["pdf", "arxiv", "semantic_scholar", "pubmed", "seed"] = "pdf"
    storage_path: str
    status: Literal["uploaded", "processed", "failed"] = "uploaded"
    page_count: int = 0
    chunk_count: int = 0
    error: str = ""
    embedding_status: Literal["pending", "embedded", "failed"] = "pending"
    created_at: str
    chunks: list[DocumentChunk] = Field(default_factory=list)
    ingestion_runs: list[IngestionRun] = Field(default_factory=list)
    extractions: PaperExtractionSet = Field(default_factory=PaperExtractionSet)


class ResearchProject(BaseModel):
    id: str
    team_id: str | None = None
    name: str
    description: str = ""
    created_at: str
    questions: list[ResearchQuestion] = Field(default_factory=list)
    briefs: list[ResearchBrief] = Field(default_factory=list)
    memory: list[MemoryItem] = Field(default_factory=list)
    source_collections: list[SourceCollection] = Field(default_factory=list)
    annotations: list[ResearchAnnotation] = Field(default_factory=list)
    experiment_plans: list[ExperimentPlan] = Field(default_factory=list)
    tasks: list[ResearchTask] = Field(default_factory=list)
    hypotheses: list[HypothesisCandidate] = Field(default_factory=list)
    uploaded_papers: list[UploadedPaper] = Field(default_factory=list)
    agent_runs: list[AgentRun] = Field(default_factory=list)
    quality_reports: list[EvidenceQualityReport] = Field(default_factory=list)
    autonomous_agents: list["AgentDefinition"] = Field(default_factory=list)
    autonomous_agent_runs: list["AgentRunRecord"] = Field(default_factory=list)
    saved_searches: list["SavedSearch"] = Field(default_factory=list)
    notifications: list["NotificationRecord"] = Field(default_factory=list)
    execution_artifacts: list["ExecutionArtifact"] = Field(default_factory=list)


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class RunQuestionRequest(BaseModel):
    question: str = Field(min_length=6, max_length=800)
    max_papers: int = Field(default=6, ge=3, le=12)
    use_memory: bool = True


class AddMemoryRequest(BaseModel):
    kind: Literal[
        "claim",
        "gap",
        "method",
        "dataset",
        "metric",
        "baseline",
        "idea",
        "experiment_idea",
        "hypothesis",
        "rejected_direction",
        "note",
        "user_note",
    ]
    content: str = Field(min_length=1, max_length=1000)
    source_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CreateCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    source_ids: list[str] = Field(default_factory=list)


class AddAnnotationRequest(BaseModel):
    target_type: Literal["brief", "source", "memory", "question"]
    target_id: str = Field(min_length=1, max_length=160)
    note: str = Field(min_length=1, max_length=1200)


class CreateExperimentPlanRequest(BaseModel):
    question_id: str | None = None
    brief_id: str | None = None
    hypothesis_id: str | None = None
    objective: str | None = Field(default=None, max_length=1000)
    template_id: str | None = None
    status: Literal["draft", "approved", "running", "completed"] = "draft"


class RecommendExperimentPlanRequest(BaseModel):
    question: str | None = Field(default=None, max_length=1000)
    brief_id: str | None = None
    hypothesis_id: str | None = None
    domain: str | None = None
    task: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class UpdateExperimentPlanRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    objective: str | None = Field(default=None, max_length=1000)
    hypothesis: str | None = Field(default=None, max_length=1000)
    datasets: list[ExperimentDataset] | None = None
    baselines: list[ExperimentBaseline] | None = None
    metrics: list[ExperimentMetric] | None = None
    ablation_config: AblationConfig | None = None
    validation_plan: ValidationPlan | None = None
    status: Literal["draft", "approved", "running", "completed"] | None = None


class GenerateScriptRequest(BaseModel):
    validation_tests: list[str] = Field(default_factory=list)
    confidence_interval: str | None = None
    correction: str | None = None


class CreateResearchTaskRequest(BaseModel):
    kind: Literal["literature_review", "experiment_plan", "hypothesis_generation", "monitor", "agent_workflow", "sandbox_run"]
    title: str = Field(min_length=1, max_length=160)
    summary: str = ""
    target_id: str | None = None


class GenerateHypothesesRequest(BaseModel):
    brief_id: str | None = None
    experiment_plan_id: str | None = None
    max_hypotheses: int = Field(default=4, ge=1, le=8)


class PromoteMemoryRequest(BaseModel):
    kind: Literal[
        "claim",
        "gap",
        "method",
        "dataset",
        "metric",
        "baseline",
        "idea",
        "experiment_idea",
        "hypothesis",
        "rejected_direction",
        "note",
        "user_note",
    ]
    content: str = Field(min_length=1, max_length=1000)
    source_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RunQuestionResponse(BaseModel):
    project: ResearchProject
    question: ResearchQuestion
    run: AgentRun
    brief: ResearchBrief


class EvidenceFeedbackRequest(BaseModel):
    rating: Literal["up", "down", "neutral"]
    note: str = Field(default="", max_length=1000)


class TenantUser(BaseModel):
    id: str
    email: str
    name: str = ""
    role: Literal["owner", "admin", "member", "viewer"] = "owner"
    password_hash: str = ""
    provider: Literal["password", "google", "github", "orcid", "local"] = "local"
    created_at: str


class Team(BaseModel):
    id: str
    name: str
    owner_user_id: str | None = None
    created_at: str


class TeamMembership(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: Literal["owner", "admin", "member", "viewer"] = "owner"
    created_at: str


class ProjectMembership(BaseModel):
    id: str
    project_id: str
    user_id: str
    team_id: str | None = None
    role: Literal["owner", "admin", "member", "viewer"] = "owner"
    created_at: str


class AuthSession(BaseModel):
    user: TenantUser
    team: Team
    role: Literal["owner", "admin", "member", "viewer"] = "owner"


class UsageEvent(BaseModel):
    id: str
    subject_id: str
    kind: str
    quantity: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class SubscriptionRecord(BaseModel):
    id: str
    team_id: str
    tier: Literal["free", "pro", "team"] = "free"
    status: Literal["active", "past_due", "cancelled"] = "active"
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""
    created_at: str


class JobRecord(BaseModel):
    id: str
    project_id: str | None = None
    kind: Literal["pdf_ingestion", "connector_search", "embedding_update", "script_generation", "export_generation", "agent_workflow", "research_pipeline"]
    status: Literal["queued", "running", "completed", "failed", "retrying"] = "queued"
    attempts: int = 0
    max_attempts: int = 3
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    created_at: str
    updated_at: str | None = None


class ObjectStorageRecord(BaseModel):
    id: str
    project_id: str | None = None
    name: str = ""
    kind: Literal["pdf", "script", "export", "sandbox_artifact", "other"] = "other"
    backend: Literal["local", "s3", "gcs", "azure"] = "local"
    uri: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    created_at: str


class AgentDefinition(BaseModel):
    id: str
    project_id: str
    type: Literal["literature_monitor", "hypothesis_generator", "experiment_planner", "experiment_runner", "result_interpreter", "notifier"]
    name: str
    goal: str
    schedule: str = ""
    status: Literal["active", "paused", "stopped"] = "active"
    created_at: str


class AgentDecision(BaseModel):
    id: str
    agent_id: str
    run_id: str
    action: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    approved: bool = False
    created_at: str


class AgentRunRecord(BaseModel):
    id: str
    agent_id: str
    project_id: str
    status: Literal["queued", "running", "paused", "completed", "failed", "stopped"] = "queued"
    current_step: str = ""
    decisions: list[AgentDecision] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    completed_at: str | None = None


class SavedSearch(BaseModel):
    id: str
    project_id: str
    query: str
    cadence: str = "weekly"
    last_run_at: str | None = None
    created_at: str


class NotificationRecord(BaseModel):
    id: str
    project_id: str
    title: str
    body: str
    status: Literal["unread", "read"] = "unread"
    created_at: str


class ExecutionArtifact(BaseModel):
    id: str
    project_id: str
    run_id: str
    kind: Literal["stdout", "stderr", "plot", "metrics", "file"] = "file"
    path: str = ""
    content: str = ""
    created_at: str


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)
    team_name: str = Field(default="Research Team", min_length=1, max_length=160)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class BillingCheckoutRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=160)
    tier: Literal["free", "pro", "team"] = "pro"
    success_url: str = "http://127.0.0.1:8000/app?billing=success"
    cancel_url: str = "http://127.0.0.1:8000/app?billing=cancelled"


class BillingWebhookRequest(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)
    id: str = ""


class QueueJobRequest(BaseModel):
    project_id: str | None = None
    kind: Literal["pdf_ingestion", "connector_search", "embedding_update", "script_generation", "export_generation", "agent_workflow", "research_pipeline"]
    payload: dict[str, Any] = Field(default_factory=dict)


class CreateAgentRequest(BaseModel):
    type: Literal["literature_monitor", "hypothesis_generator", "experiment_planner", "experiment_runner", "result_interpreter", "notifier"]
    name: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=1, max_length=1200)
    schedule: str = ""


class BootstrapTenantRequest(BaseModel):
    email: str = Field(default="local@example.com", max_length=320)
    team_name: str = Field(default="Local Workspace", min_length=1, max_length=160)
    tier: Literal["free", "pro", "team"] = "free"


class RecordUsageRequest(BaseModel):
    subject_id: str = Field(min_length=1, max_length=160)
    kind: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateSavedSearchRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=160)
    query: str = Field(min_length=1, max_length=800)
    cadence: str = Field(default="weekly", max_length=80)


class RunAgentStepRequest(BaseModel):
    query: str | None = Field(default=None, max_length=800)
    experiment_plan_id: str | None = None
    approve: bool = False


class SandboxRunRequest(BaseModel):
    script: str = Field(min_length=1, max_length=20000)
    timeout_seconds: int = Field(default=5, ge=1, le=60)


ResearchProject.model_rebuild()
