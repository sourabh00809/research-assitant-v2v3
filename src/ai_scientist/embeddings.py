from __future__ import annotations

import hashlib
import logging
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

from .models import ChunkRankingResult, DocumentChunk, EmbeddingRecord, MemoryItem, ScoredResult, new_id, utc_now

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIMENSIONS = 96

SYNONYM_GROUPS = [
    {"research", "scientific", "academic", "science"},
    {"agent", "agents", "assistant", "copilot", "autonomous"},
    {"method", "methodology", "approach", "framework", "pipeline"},
    {"evaluate", "evaluation", "validation", "benchmark", "metric", "metrics"},
    {"baseline", "comparison", "compare"},
    {"dataset", "data", "corpus", "benchmark"},
    {"retrieval", "search", "rag", "evidence"},
    {"memory", "context", "prior"},
    {"trust", "trustworthy", "reliable", "quality", "rigor"},
    {"chunk", "passage", "document", "paper"},
]


class EmbeddingService:
    def __init__(self, model: str = DEFAULT_EMBEDDING_MODEL):
        self.model = model
        self._sentence_transformer = None
        if model.startswith("sentence-transformers/"):
            self._init_sentence_transformer(model)

    def _init_sentence_transformer(self, model: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._sentence_transformer = SentenceTransformer(model.replace("sentence-transformers/", ""))
            logger.info("Loaded sentence-transformers model: %s", model)
        except ImportError:
            logger.warning("sentence-transformers not installed, falling back to hash embeddings for model: %s", model)
            self._sentence_transformer = None
        except Exception as exc:
            logger.warning("Failed to load sentence-transformers model %s: %s", model, exc)
            self._sentence_transformer = None

    def embed_text(self, text: str) -> list[float]:
        if self._sentence_transformer is not None:
            try:
                vector = self._sentence_transformer.encode(text).tolist()
                return [float(v) for v in vector]
            except Exception:
                pass
        vector = [0.0] * VECTOR_DIMENSIONS
        for token in expand_terms(tokenize(text)):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % VECTOR_DIMENSIONS
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return normalize(vector)

    def embed_batch(self, texts: Iterable[str]) -> list[list[float]]:
        if self._sentence_transformer is not None:
            try:
                return [self.embed_text(text) for text in texts]
            except Exception:
                pass
        return [self.embed_text(text) for text in texts]

    def record(self, artifact_type: str, artifact_id: str, text: str) -> EmbeddingRecord:
        return EmbeddingRecord(
            id=new_id("emb"),
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            model=self.model,
            vector=self.embed_text(text),
            created_at=utc_now(),
        )


@dataclass
class HybridScore:
    semantic_score: float
    keyword_score: float
    final_score: float


class VectorSearchService:
    def __init__(self, embedding_service: EmbeddingService | None = None):
        self.embedding_service = embedding_service or EmbeddingService()

    def score(self, query: str, text: str) -> HybridScore:
        query_vector = self.embedding_service.embed_text(query)
        text_vector = self.embedding_service.embed_text(text)
        semantic = cosine_similarity(query_vector, text_vector)
        keyword = keyword_score(query, text)
        final = round((0.65 * semantic) + (0.35 * keyword), 3)
        return HybridScore(round(semantic, 3), round(keyword, 3), final)

    def search(
        self,
        query: str,
        artifacts: Iterable[tuple[str, str, str]],
        top_k: int = 8,
        threshold: float = 0.0,
    ) -> list[ScoredResult]:
        results: list[ScoredResult] = []
        for artifact_type, artifact_id, text in artifacts:
            score = self.score(query, text)
            if score.final_score < threshold:
                continue
            results.append(
                ScoredResult(
                    artifact_type=artifact_type,
                    artifact_id=artifact_id,
                    semantic_score=score.semantic_score,
                    keyword_score=score.keyword_score,
                    final_score=score.final_score,
                )
            )
        return sorted(results, key=lambda item: item.final_score, reverse=True)[:top_k]


def rank_chunks(query: str, chunks: list[DocumentChunk], limit: int = 8) -> list[ChunkRankingResult]:
    search = VectorSearchService()
    ranked: list[ChunkRankingResult] = []
    for chunk in chunks:
        score = search.score(query, chunk.text)
        section = section_label(chunk.text)
        position_weight = section_weight(section)
        if len(tokenize(chunk.text)) < 50:
            position_weight *= 0.85
        ranked.append(
            ChunkRankingResult(
                chunk_id=chunk.id,
                semantic_score=score.semantic_score,
                position_weight=round(position_weight, 3),
                final_score=round(score.final_score * position_weight, 3),
                section_label=section,
            )
        )
    return sorted(ranked, key=lambda item: item.final_score, reverse=True)[:limit]


def memory_relevance(query: str, memory: list[MemoryItem], limit: int = 5) -> list[tuple[MemoryItem, float, str]]:
    search = VectorSearchService()
    scored: list[tuple[MemoryItem, float, str]] = []
    query_terms = tokenize(query)
    for item in memory:
        if item.status != "active":
            continue
        text = " ".join([item.kind, item.content, *item.tags])
        score = search.score(query, text)
        if score.keyword_score == 0 and score.semantic_score < 0.35:
            continue
        lowered = item.content.lower()
        influence = "contradicted" if any(term in lowered for term in ["not ", "avoid", "rejected", "contradict"]) else "extended"
        if len(query_terms & tokenize(text)) >= 2:
            influence = "confirmed"
        scored.append((item, score.final_score, influence))
    return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True))))


def keyword_score(query: str, text: str) -> float:
    query_terms = tokenize(query)
    text_terms = tokenize(text)
    if not query_terms:
        return 0.0
    return len(query_terms & text_terms) / len(query_terms)


def tokenize(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "what", "does", "are", "how", "can", "use", "using"}
    return {term for term in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower()) if term not in stop}


def expand_terms(terms: set[str]) -> list[str]:
    expanded = set(terms)
    for group in SYNONYM_GROUPS:
        if terms & group:
            expanded.add("_".join(sorted(group)))
    return sorted(expanded)


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def section_label(text: str):
    head = text[:160].lower()
    patterns = [
        ("abstract", r"\babstract\b"),
        ("introduction", r"\bintroduction\b"),
        ("method", r"\b(method|methodology|approach|materials)\b"),
        ("results", r"\b(results|findings)\b"),
        ("discussion", r"\bdiscussion\b"),
        ("conclusion", r"\b(conclusion|conclusions)\b"),
    ]
    for label, pattern in patterns:
        if re.search(pattern, head):
            return label
    return "unknown"


def section_weight(label: str) -> float:
    return {
        "abstract": 1.12,
        "conclusion": 1.08,
        "method": 1.06,
        "results": 1.04,
        "discussion": 1.02,
        "introduction": 1.0,
    }.get(label, 0.95)
