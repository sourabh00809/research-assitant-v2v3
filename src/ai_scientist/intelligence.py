from __future__ import annotations

import re

from .models import (
    BaselineMention,
    DatasetMention,
    DocumentChunk,
    EvidenceItem,
    EvidenceQualityReport,
    ExtractedClaim,
    FutureWorkItem,
    AssumptionItem,
    LimitationItem,
    MethodologyItem,
    MetricMention,
    PaperComparison,
    PaperExtractionSet,
    PaperSource,
    new_id,
    utc_now,
)


KEYWORDS = {
    "method": ["method", "approach", "system", "model", "framework", "pipeline", "architecture"],
    "dataset": ["dataset", "corpus", "data", "benchmark", "samples"],
    "metric": ["metric", "evaluation", "accuracy", "f1", "auc", "performance", "score"],
    "baseline": ["baseline", "compare", "comparison", "state-of-the-art", "sota"],
    "limitation": ["limitation", "depends", "sensitive", "challenge", "caveat", "weakness"],
    "future_work": ["future", "remain", "open", "next", "extend", "further"],
    "assumption": ["assume", "assumption", "requires", "depends", "under the condition"],
}


def extract_from_chunks(paper_id: str, chunks: list[DocumentChunk], source_id_prefix: str = "pdf") -> PaperExtractionSet:
    extraction = PaperExtractionSet()
    for chunk in chunks:
        source_id = f"{source_id_prefix}_{chunk.id}"
        add_text_extractions(
            extraction=extraction,
            text=chunk.text,
            paper_id=paper_id,
            source_id=source_id,
            chunk_id=chunk.id,
            page_number=chunk.page_number,
            confidence="medium",
            confidence_score=0.68,
        )
    return extraction


def extract_from_sources(papers: list[PaperSource]) -> PaperExtractionSet:
    extraction = PaperExtractionSet()
    for paper in papers:
        add_text_extractions(
            extraction=extraction,
            text=paper.abstract,
            paper_id=paper.paper_id or paper.id,
            source_id=paper.id,
            chunk_id=paper.chunk_id,
            page_number=paper.page_number,
            confidence="medium" if paper.source_type in {"seed", "pdf"} else "low",
            confidence_score=0.66 if paper.source_type in {"seed", "pdf"} else 0.46,
        )
    return extraction


def add_text_extractions(
    extraction: PaperExtractionSet,
    text: str,
    paper_id: str,
    source_id: str,
    chunk_id: str | None,
    page_number: int | None,
    confidence: str,
    confidence_score: float,
) -> None:
    sentences = split_sentences(text)
    claim = first_meaningful(sentences)
    if claim:
        extraction.claims.append(
            ExtractedClaim(
                id=new_id("claim"),
                paper_id=paper_id,
                source_id=source_id,
                text=claim,
                supporting_text=claim,
                confidence=confidence,
                confidence_score=confidence_score,
                page_number=page_number,
                chunk_id=chunk_id,
                created_at=utc_now(),
            )
        )
    for kind, keywords in KEYWORDS.items():
        sentence = keyword_sentence(sentences, keywords)
        if not sentence:
            continue
        common = {
            "paper_id": paper_id,
            "source_id": source_id,
            "text": sentence,
            "supporting_text": sentence,
            "confidence": confidence,
            "confidence_score": confidence_score,
            "page_number": page_number,
            "chunk_id": chunk_id,
            "created_at": utc_now(),
        }
        if kind == "method":
            extraction.methods.append(MethodologyItem(id=new_id("method"), **common))
        elif kind == "dataset":
            extraction.datasets.append(DatasetMention(id=new_id("dataset"), **common))
        elif kind == "metric":
            extraction.metrics.append(MetricMention(id=new_id("metric"), **common))
        elif kind == "baseline":
            extraction.baselines.append(BaselineMention(id=new_id("baseline"), **common))
        elif kind == "limitation":
            extraction.limitations.append(LimitationItem(id=new_id("limitation"), **common))
        elif kind == "future_work":
            extraction.future_work.append(FutureWorkItem(id=new_id("future"), **common))
        elif kind == "assumption":
            extraction.assumptions.append(AssumptionItem(id=new_id("assumption"), **common))


def evidence_from_extractions(extractions: PaperExtractionSet) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for artifact in extractions.all_items():
        items.append(
            EvidenceItem(
                id=new_id("ev"),
                source_id=artifact.source_id,
                claim=artifact.text,
                support=artifact.supporting_text,
                confidence=artifact.confidence,
                confidence_score=artifact.confidence_score,
                extraction_type=artifact.kind,
                extraction_method=artifact.extraction_method,
                source_quote=artifact.supporting_text,
                source_span=artifact.supporting_text[:180],
                paper_id=artifact.paper_id,
                chunk_id=artifact.chunk_id,
                page_number=artifact.page_number,
            )
        )
    return items


def build_quality_report(brief_id: str, evidence: list[EvidenceItem], matrix: list[PaperComparison]) -> EvidenceQualityReport:
    factual_claims = [item for item in evidence if item.extraction_type == "claim"]
    cited = [item for item in evidence if item.source_id and item.support]
    unsupported = [
        item.claim
        for item in evidence
        if not item.source_id or not item.support or item.confidence == "low" and item.confidence_score < 0.35
    ]
    missing_datasets = [row.source_id for row in matrix if row.dataset.startswith("Dataset not explicit")]
    missing_baselines = [row.source_id for row in matrix if row.baselines.startswith("Baselines not explicit")]
    missing_metrics = [row.source_id for row in matrix if row.metrics.startswith("Metrics not explicit")]
    missing_validation = [row.source_id for row in matrix if row.validation.startswith("Validation design not explicit")]
    weak_signals = [f"{row.source_id}: {flag}" for row in matrix for flag in row.quality_flags]
    insufficient = not evidence or len(factual_claims) == 0 or (len(cited) / max(len(evidence), 1)) < 0.5
    coverage = round(len(cited) / max(len(evidence), 1), 3)
<<<<<<< HEAD
    semantic_hits = len([item for item in evidence if item.retrieval_method == "semantic"])
    keyword_hits = len([item for item in evidence if item.retrieval_method == "keyword"])
    hybrid_hits = len([item for item in evidence if item.retrieval_method == "hybrid"])
    embedded = len([item for item in evidence if item.semantic_score is not None])
    connectors = sorted({item.source_type for item in evidence if item.source_type})
=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
    speculative = []
    if insufficient:
        speculative.append("Insufficient extracted evidence; any research directions should be treated as hypotheses to investigate, not conclusions.")
    return EvidenceQualityReport(
        id=new_id("quality"),
        brief_id=brief_id,
        citation_coverage=coverage,
        unsupported_claims=unsupported[:10],
        weak_methodology_signals=dedupe(weak_signals)[:10],
        missing_datasets=dedupe(missing_datasets)[:10],
        missing_baselines=dedupe(missing_baselines)[:10],
        missing_metrics=dedupe(missing_metrics)[:10],
        missing_statistical_validation=dedupe(missing_validation)[:10],
        speculative_conclusions=speculative,
        insufficient_evidence=insufficient,
<<<<<<< HEAD
        semantic_hits=semantic_hits,
        keyword_hits=keyword_hits,
        hybrid_hits=hybrid_hits,
        embedding_coverage=round(embedded / max(len(evidence), 1), 3),
        connectors_used=connectors,
=======
>>>>>>> 6a7e9446766ffc975781f6ee2ded51bd711ceb44
        summary=quality_summary(coverage, insufficient, weak_signals),
        created_at=utc_now(),
    )


def quality_summary(citation_coverage: float, insufficient: bool, weak_signals: list[str]) -> str:
    if insufficient:
        return "Evidence is insufficient for strong conclusions; use the brief as a review plan and hypothesis seed."
    if weak_signals:
        return "Evidence is citation-linked, but methodology reporting has gaps that need full-text review."
    return "Evidence is citation-linked with no major deterministic methodology gaps detected."


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def first_meaningful(sentences: list[str]) -> str:
    return next((sentence for sentence in sentences if len(sentence) > 35), sentences[0] if sentences else "")


def keyword_sentence(sentences: list[str], keywords: list[str]) -> str:
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            return sentence[:600]
    return ""


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
