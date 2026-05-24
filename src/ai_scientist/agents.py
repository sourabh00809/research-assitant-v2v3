from __future__ import annotations

import re

from .embeddings import memory_relevance
from .models import (
    AgentRun,
    AgentStep,
    EvidenceItem,
    MemoryRelevanceScore,
    PaperComparison,
    ResearchBrief,
    ResearchQuestion,
    MemoryItem,
    new_id,
    utc_now,
)
from .retrieval import SearchService
from .ai_providers import AIProvider, DeterministicProvider
from .intelligence import build_quality_report, evidence_from_extractions, extract_from_sources


class ResearchOrchestrator:
    def __init__(self, search_service: SearchService | None = None, ai_provider: AIProvider | None = None):
        self.search_service = search_service or SearchService()
        self.ai_provider = ai_provider or DeterministicProvider()

    def run(
        self,
        question: ResearchQuestion,
        max_papers: int = 6,
        memory: list[MemoryItem] | None = None,
        extra_sources=None,
    ) -> tuple[AgentRun, ResearchBrief]:
        run = AgentRun(id=new_id("run"), question_id=question.id, status="running", started_at=utc_now(), provider=self.ai_provider.name)
        memory_scores = memory_relevance(question.text, memory or [])
        memory_context = [item for item, _, _ in memory_scores]
        run.steps.append(
            AgentStep(
                name="Memory Context Agent",
                status="completed",
                summary=f"Selected {len(memory_context)} semantically relevant memory items to condition the investigation.",
                output={
                    "memory_ids": [item.id for item in memory_context],
                    "similarity_scores": {item.id: score for item, score, _ in memory_scores},
                },
            )
        )

        papers = self.search_service.search(question.text, max_papers=max_papers, extra_sources=extra_sources or [])
        run.steps.append(
            AgentStep(
                name="Search Agent",
                status="completed",
                summary=f"Retrieved, deduplicated, and hybrid-ranked {len(papers)} candidate sources.",
                output={"source_ids": [paper.id for paper in papers], "sources": {paper.id: paper.sources for paper in papers}},
            )
        )

        run.steps.append(
            AgentStep(
                name="Relevance Agent",
                status="completed",
                summary="Ranked papers by hybrid semantic similarity, keyword score, and methodology usefulness.",
                output={
                    "rankings": [
                        {"source_id": paper.id, "score": paper.relevance_score, "reason": paper.relevance_reason}
                        for paper in papers
                    ]
                },
            )
        )

        source_extractions = extract_from_sources(papers)
        evidence = evidence_from_extractions(source_extractions)
<<<<<<< HEAD
        apply_retrieval_metadata(question.text, papers, evidence)
=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
        matrix = build_matrix(papers)
        run.steps.append(
            AgentStep(
                name="Extraction Agent",
                status="completed",
                summary=f"Extracted {len(evidence)} structured, citation-linked artifacts and {len(matrix)} comparison rows.",
                output={
                    "evidence_count": len(evidence),
                    "matrix_count": len(matrix),
                    "claim_count": len(source_extractions.claims),
                    "method_count": len(source_extractions.methods),
                    "dataset_count": len(source_extractions.datasets),
                    "metric_count": len(source_extractions.metrics),
                    "baseline_count": len(source_extractions.baselines),
                    "limitation_count": len(source_extractions.limitations),
                    "future_work_count": len(source_extractions.future_work),
                    "assumption_count": len(source_extractions.assumptions),
                },
            )
        )

        critique = critique_methods(matrix)
        weak_flags = critique["weak_flags"]
        open_problems = critique["open_problems"]
        run.steps.append(
            AgentStep(
                name="Methodology Critique Agent",
                status="completed",
                summary="Scored methodology reporting and flagged missing baselines, validation, datasets, and metrics.",
                output=critique,
            )
        )

        provider_result = self.ai_provider.synthesize(f"Synthesize research brief for: {question.text}")
        run.warnings.extend(provider_result.warnings)
        if provider_result.provider:
            run.provider = provider_result.provider
        brief = synthesize_brief(
            question.text,
            papers,
            evidence,
            matrix,
            critique,
            memory_context,
<<<<<<< HEAD
            memory_scores,
=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
            provider=run.provider,
            provider_summary=provider_result.text,
        )
        brief.source_modes_used = sorted({paper.source_type for paper in papers})
        quality_report = build_quality_report(brief.id, evidence, matrix)
        brief.quality_report_id = quality_report.id
        brief.unsupported_claims = quality_report.unsupported_claims
        brief.speculative_suggestions = quality_report.speculative_conclusions
        brief.memory_used = [item.id for item in memory_context]
<<<<<<< HEAD
        brief.memory_relevance_scores = [
            MemoryRelevanceScore(memory_item_id=item.id, similarity_score=score, influence=influence)
            for item, score, influence in memory_scores
        ]
=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
        if quality_report.insufficient_evidence:
            brief.key_findings = ["Insufficient evidence: retrieved sources do not support strong conclusions yet."]
        brief.quality_report = quality_report
        run.steps.append(
            AgentStep(
                name="Synthesis Agent",
                status="completed",
                summary="Produced a citation-grounded research brief using only extracted evidence.",
                output={"brief_id": brief.id, "quality_report_id": quality_report.id},
            )
        )

        run.steps.append(
            AgentStep(
                name="Memory Agent",
                status="completed",
                summary="Prepared durable findings and linked this run back to project memory.",
                output={
                    "suggested_memory": brief.open_problems[:2] + brief.suggested_next_directions[:2],
                    "memory_context_used": brief.memory_context_used,
                },
            )
        )
        run.status = "completed"
        run.completed_at = utc_now()
        return run, brief


def extract_evidence(papers) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    for paper in papers:
        sentences = split_sentences(paper.abstract)
        claim_sentence = first_meaningful(sentences) or paper.abstract[:240]
        evidence.append(
            EvidenceItem(
                id=new_id("ev"),
                source_id=paper.id,
                claim=claim_sentence,
                support=claim_sentence,
                confidence="medium" if paper.source == "seed" else "low",
                extraction_type="claim",
                paper_id=paper.paper_id,
                chunk_id=paper.chunk_id,
                page_number=paper.page_number,
            )
        )

        method = extract_keyword_sentence(sentences, ["method", "approach", "system", "model", "framework"])
        if method:
            evidence.append(
                EvidenceItem(
                    id=new_id("ev"),
                    source_id=paper.id,
                    claim=f"Method signal: {method}",
                    support=method,
                    confidence="medium",
                    extraction_type="method",
                    paper_id=paper.paper_id,
                    chunk_id=paper.chunk_id,
                    page_number=paper.page_number,
                )
            )

        limitation = extract_keyword_sentence(sentences, ["limitation", "depends", "sensitive", "challenge", "remain"])
        if limitation:
            evidence.append(
                EvidenceItem(
                    id=new_id("ev"),
                    source_id=paper.id,
                    claim=f"Limitation signal: {limitation}",
                    support=limitation,
                    confidence="medium",
                    extraction_type="limitation",
                    paper_id=paper.paper_id,
                    chunk_id=paper.chunk_id,
                    page_number=paper.page_number,
                )
            )
        dataset = extract_keyword_sentence(sentences, ["dataset", "corpus", "data", "benchmark"])
        if dataset:
            evidence.append(
                EvidenceItem(
                    id=new_id("ev"),
                    source_id=paper.id,
                    claim=f"Dataset signal: {dataset}",
                    support=dataset,
                    confidence="medium",
                    extraction_type="dataset",
                    paper_id=paper.paper_id,
                    chunk_id=paper.chunk_id,
                    page_number=paper.page_number,
                )
            )
        metric = extract_keyword_sentence(sentences, ["metric", "evaluation", "baseline", "confidence interval", "performance"])
        if metric:
            evidence.append(
                EvidenceItem(
                    id=new_id("ev"),
                    source_id=paper.id,
                    claim=f"Evaluation signal: {metric}",
                    support=metric,
                    confidence="medium",
                    extraction_type="metric",
                    paper_id=paper.paper_id,
                    chunk_id=paper.chunk_id,
                    page_number=paper.page_number,
                )
            )
    return evidence


def build_matrix(papers) -> list[PaperComparison]:
    matrix: list[PaperComparison] = []
    for paper in papers:
        text = paper.abstract
        method = extract_aspect(text, ["method", "approach", "system", "model", "framework"]) or "Method not explicit in available abstract."
        dataset = extract_aspect(text, ["dataset", "corpus", "data", "benchmark"]) or "Dataset not explicit in available abstract."
        metrics = extract_aspect(text, ["metric", "evaluation", "baseline", "confidence interval", "performance"]) or "Metrics not explicit in available abstract."
        assumptions = extract_aspect(text, ["depends", "conditioning", "assumes", "requires"]) or "Assumptions require full-text review."
        limitations = extract_aspect(text, ["limitation", "sensitive", "challenge", "caveat", "remain"]) or "Limitations not explicit in available abstract."
        future_work = extract_aspect(text, ["future", "remain", "open", "adoption", "oversight"]) or "Future work not explicit in available abstract."
        baselines = extract_aspect(text, ["baseline", "compare", "comparison", "benchmark"]) or "Baselines not explicit in available abstract."
        validation = extract_aspect(text, ["confidence interval", "statistical", "significance", "random seed", "reproducibility", "evaluation"]) or "Validation design not explicit in available abstract."
        score, flags = score_methodology(dataset, metrics, baselines, validation, limitations)
        matrix.append(
            PaperComparison(
                source_id=paper.id,
                method=method,
                dataset=dataset,
                metrics=metrics,
                assumptions=assumptions,
                limitations=limitations,
                future_work=future_work,
                baselines=baselines,
                validation=validation,
                quality_score=score,
                quality_flags=flags,
            )
        )
    return matrix


def critique_methods(matrix: list[PaperComparison]) -> dict:
    weak_flags: list[str] = []
    open_problems: list[str] = []
    baseline_recommendations: list[str] = []
    statistical_validation: list[str] = []
    for row in matrix:
        weak_flags.extend(f"{row.source_id}: {flag}" for flag in row.quality_flags)
        if row.baselines.startswith("Baselines not explicit"):
            baseline_recommendations.append(
                f"{row.source_id}: require named baselines or prior methods before treating reported gains as meaningful."
            )
        if row.validation.startswith("Validation design not explicit"):
            statistical_validation.append(
                f"{row.source_id}: add confidence intervals, repeated runs, or significance tests before relying on conclusions."
            )
        if "require full-text" in row.assumptions:
            open_problems.append(f"{row.source_id}: inspect the full text to validate assumptions and boundary conditions.")
        if row.quality_score < 60:
            open_problems.append(f"{row.source_id}: methodology reporting score is {row.quality_score}/100; prioritize full-text audit.")

    if not weak_flags:
        weak_flags.append("The selected abstracts contain some evaluation signal, but claims still require full-text verification.")
    if not open_problems:
        open_problems.append("Compare whether the reported methods generalize beyond their original benchmark settings.")
    if not baseline_recommendations:
        baseline_recommendations.append("Compare against the strongest recent baseline and at least one simple baseline.")
    if not statistical_validation:
        statistical_validation.append("Report uncertainty with confidence intervals, repeated trials, or significance tests where applicable.")
    open_problems.append("Build a cross-paper evidence table before treating any gap as a novel research opportunity.")
    return {
        "weak_flags": dedupe(weak_flags)[:10],
        "open_problems": dedupe(open_problems)[:10],
        "baseline_recommendations": dedupe(baseline_recommendations)[:8],
        "statistical_validation": dedupe(statistical_validation)[:8],
    }


def synthesize_brief(
    question_text: str,
    papers,
    evidence,
    matrix,
    critique,
    memory_context: list[MemoryItem],
<<<<<<< HEAD
    memory_scores: list[tuple[MemoryItem, float, str]] | None = None,
=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
    provider: str = "deterministic",
    provider_summary: str = "",
) -> ResearchBrief:
    top_papers = papers[: min(4, len(papers))]
    key_findings = [
        f"{paper.title} is relevant because {paper.relevance_reason} [{paper.id}]"
        for paper in top_papers
    ]
    methodology_assessment = [
        f"{row.source_id}: score={row.quality_score}/100 | method='{row.method}' | metrics='{row.metrics}' | baselines='{row.baselines}'"
        for row in matrix[:6]
    ]
    next_directions = [
        "Run a full-text review for the highest-ranked papers before making novelty claims.",
        "Convert recurring limitations into testable research questions with explicit datasets and evaluation metrics.",
        "Track rejected directions in memory so future agent runs do not repeat weak ideas.",
    ]
    if memory_context:
        next_directions.insert(0, "Reconcile this brief against prior project memory before adding new research directions.")
    return ResearchBrief(
        id=new_id("brief"),
        question_id="pending",
        title=f"Research Brief: {question_text[:90]}",
        question_interpretation=(
            "The platform interprets this as a literature investigation requiring relevant sources, "
            "method comparison, evidence quality checks, and cautious gap identification."
        ),
        key_findings=key_findings or ["Insufficient evidence: no relevant sources were retrieved."],
        evidence_items=evidence,
        paper_matrix=matrix,
        methodology_assessment=methodology_assessment,
        weak_evidence_flags=critique["weak_flags"],
        open_problems=critique["open_problems"],
        suggested_next_directions=next_directions,
        baseline_recommendations=critique["baseline_recommendations"],
        statistical_validation=critique["statistical_validation"],
        provider_used=provider,
        provider_summary=provider_summary[:2000],
        memory_context_used=[
            f"{item.kind}: {item.content} [{item.id}; sim={score:.2f}; {influence}]"
            for item, score, influence in (memory_scores or [(item, 0.0, "extended") for item in memory_context])
        ],
        bibliography=[paper.citation for paper in papers],
        created_at=utc_now(),
    )


def score_methodology(dataset: str, metrics: str, baselines: str, validation: str, limitations: str) -> tuple[int, list[str]]:
    score = 100
    flags: list[str] = []
    checks = [
        (dataset.startswith("Dataset not explicit"), 20, "dataset or corpus details are not explicit in the available abstract"),
        (metrics.startswith("Metrics not explicit"), 20, "evaluation metrics are not explicit in the available abstract"),
        (baselines.startswith("Baselines not explicit"), 18, "baseline comparisons are not explicit in the available abstract"),
        (validation.startswith("Validation design not explicit"), 18, "statistical validation design is not explicit in the available abstract"),
        (limitations.startswith("Limitations not explicit"), 12, "limitations are not explicit in the available abstract"),
    ]
    for failed, penalty, flag in checks:
        if failed:
            score -= penalty
            flags.append(flag)
    return max(score, 0), flags


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def first_meaningful(sentences: list[str]) -> str:
    return next((sentence for sentence in sentences if len(sentence) > 40), sentences[0] if sentences else "")


def extract_keyword_sentence(sentences: list[str], keywords: list[str]) -> str:
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            return sentence
    return ""


def extract_aspect(text: str, keywords: list[str]) -> str:
    sentence = extract_keyword_sentence(split_sentences(text), keywords)
    return sentence[:260]


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def apply_retrieval_metadata(question_text: str, papers, evidence: list[EvidenceItem]) -> None:
    paper_by_id = {paper.id: paper for paper in papers}
    for item in evidence:
        paper = paper_by_id.get(item.source_id)
        if not paper:
            continue
        item.semantic_score = infer_semantic_score(paper.relevance_reason, paper.relevance_score)
        item.keyword_score = infer_keyword_score(paper.relevance_reason)
        item.retrieval_method = "hybrid" if item.semantic_score and item.keyword_score else "semantic" if item.semantic_score else "keyword"
        item.source_type = paper.source_type
        item.source_badges = paper.sources or [paper.source_type]


def infer_semantic_score(reason: str, fallback: float) -> float:
    match = re.search(r"semantic=([0-9.]+)", reason)
    return round(float(match.group(1)), 3) if match else fallback


def infer_keyword_score(reason: str) -> float:
    match = re.search(r"keyword=([0-9.]+)", reason)
    return round(float(match.group(1)), 3) if match else 0.0


def select_memory_context(question_text: str, memory: list[MemoryItem], limit: int = 5) -> list[MemoryItem]:
    query_terms = tokenize(question_text)
    scored: list[tuple[int, MemoryItem]] = []
    for item in memory:
        if item.status != "active":
            continue
        item_terms = tokenize(" ".join([item.kind, item.content, *item.tags]))
        score = len(query_terms & item_terms)
        if item.kind in {"gap", "rejected_direction"}:
            score += 1
        if score > 0:
            scored.append((score, item))
    return [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)[:limit]]


def tokenize(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "what", "does", "are", "how", "can", "use"}
    return {term for term in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower()) if term not in stop}
