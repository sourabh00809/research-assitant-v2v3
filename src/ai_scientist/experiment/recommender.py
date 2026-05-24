from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any

from ..models import ExperimentBaseline, ExperimentDataset, ExperimentMetric, ResearchBrief
from .templates import load_template


def classify_domain_task(text: str, brief: ResearchBrief | None = None) -> tuple[str, str, str]:
    corpus = " ".join([text, *(item.claim for item in (brief.evidence_items if brief else []))]).lower()
    if any(term in corpus for term in ["image", "vision", "cifar", "resnet", "classification"]):
        return "vision", "image_classification", "image_classification"
    if any(term in corpus for term in ["rag", "retrieval", "citation", "evidence"]):
        return "ai", "rag_evaluation", "rag_evaluation"
    if any(term in corpus for term in ["biomed", "clinical", "patient", "pubmed", "drug"]):
        return "biomed", "prediction", "biomed_prediction"
    if any(term in corpus for term in ["survey", "social", "participant", "policy"]):
        return "social_science", "survey_analysis", "social_science_survey"
    return "nlp", "text_classification", "nlp_classification"


def recommend(brief: ResearchBrief | None, question: str = "", domain: str | None = None, task: str | None = None, top_k: int = 5) -> dict[str, Any]:
    inferred_domain, inferred_task, template_id = classify_domain_task(" ".join([question, domain or "", task or ""]), brief)
    template = load_template(template_id)
    datasets = dataset_recommendations(brief, template, top_k)
    baselines = baseline_recommendations(brief, template, top_k)
    metrics = metric_recommendations(template)
    return {
        "domain": domain or inferred_domain,
        "task": task or inferred_task,
        "template_id": template_id,
        "datasets": [item.model_dump() for item in datasets],
        "baselines": [item.model_dump() for item in baselines],
        "metrics": [item.model_dump() for item in metrics],
        "ablation_vars": template.get("ablation_vars", []),
        "validation": template.get("validation", "5-fold cross-validation"),
    }


def dataset_recommendations(brief: ResearchBrief | None, template: dict[str, Any], top_k: int) -> list[ExperimentDataset]:
    items: list[ExperimentDataset] = []
    for name, count in extracted_counts(brief, "dataset").most_common():
        items.append(ExperimentDataset(name=name, source="literature", confidence=min(0.95, 0.65 + count * 0.1), rationale="Mentioned in reviewed evidence."))
    for dataset in template.get("recommended_datasets", []):
        if isinstance(dataset, dict):
            items.append(ExperimentDataset(name=dataset.get("name", ""), source=dataset.get("source", "template"), url=dataset.get("url", ""), confidence=0.72, rationale="Recommended by domain template."))
        else:
            items.append(ExperimentDataset(name=str(dataset), source="template", confidence=0.68, rationale="Recommended by domain template."))
    items.extend(search_huggingface(template.get("domain", ""), top_k=2))
    return dedupe_datasets(items)[:top_k]


def baseline_recommendations(brief: ResearchBrief | None, template: dict[str, Any], top_k: int) -> list[ExperimentBaseline]:
    items: list[ExperimentBaseline] = []
    for name, count in extracted_counts(brief, "baseline").most_common():
        items.append(ExperimentBaseline(name=name, description="Baseline mentioned in reviewed literature.", reference="literature", confidence=min(0.95, 0.65 + count * 0.1), rationale="Mentioned in reviewed evidence."))
    for baseline in template.get("baseline_models", []):
        items.append(ExperimentBaseline(name=str(baseline), description="Template baseline.", reference="template", confidence=0.7, rationale="Recommended by domain template."))
    items.extend(search_papers_with_code(template.get("task", ""), top_k=2))
    return dedupe_baselines(items)[:top_k]


def metric_recommendations(template: dict[str, Any]) -> list[ExperimentMetric]:
    metrics = []
    for metric in template.get("metrics", []):
        lower = str(metric).lower()
        metrics.append(
            ExperimentMetric(
                name=str(metric),
                formula=metric_formula(lower),
                higher_is_better=not any(term in lower for term in ["error", "loss", "latency", "cost"]),
                rationale="Recommended by domain template.",
            )
        )
    return metrics


def extracted_counts(brief: ResearchBrief | None, extraction_type: str) -> Counter:
    counts: Counter = Counter()
    if not brief:
        return counts
    for item in brief.evidence_items:
        if item.extraction_type != extraction_type:
            continue
        name = item.claim.replace("Dataset signal:", "").replace("Evaluation signal:", "").replace("Method signal:", "").strip()
        counts[name[:140]] += 1
    return counts


def search_huggingface(domain: str, top_k: int) -> list[ExperimentDataset]:
    if os.getenv("AI_SCIENTIST_HF_ENABLED", "false").lower() != "true":
        return []
    query = urllib.parse.quote(domain or "classification")
    url = f"https://huggingface.co/api/datasets?search={query}&limit={top_k}"
    try:
        request = urllib.request.Request(url)
        token = os.getenv("HUGGINGFACE_API_TOKEN")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    return [
        ExperimentDataset(name=item.get("id", "hf_dataset"), source="huggingface", url=f"https://huggingface.co/datasets/{item.get('id', '')}", confidence=0.62, rationale="Matched by Hugging Face dataset search.")
        for item in payload[:top_k]
    ]


def search_papers_with_code(task: str, top_k: int) -> list[ExperimentBaseline]:
    if os.getenv("AI_SCIENTIST_PWC_ENABLED", "false").lower() != "true":
        return []
    query = urllib.parse.quote(task or "classification")
    url = f"https://paperswithcode.com/api/v1/papers/?q={query}"
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    return [
        ExperimentBaseline(name=item.get("title", "Papers with Code baseline"), description="Matched by Papers with Code.", reference=item.get("url_abs", ""), confidence=0.6, rationale="External benchmark search result.")
        for item in payload.get("results", [])[:top_k]
    ]


def metric_formula(name: str) -> str:
    formulas = {
        "accuracy": "(tp + tn) / (tp + tn + fp + fn)",
        "f1": "2 * precision * recall / (precision + recall)",
        "f1_macro": "mean(classwise_f1)",
        "roc_auc": "area under ROC curve",
        "citation_support": "supported_claims / total_claims",
    }
    return formulas.get(name, "computed by task-specific evaluator")


def dedupe_datasets(items: list[ExperimentDataset]) -> list[ExperimentDataset]:
    seen = set()
    result = []
    for item in items:
        key = item.name.lower()
        if not item.name or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def dedupe_baselines(items: list[ExperimentBaseline]) -> list[ExperimentBaseline]:
    seen = set()
    result = []
    for item in items:
        key = item.name.lower()
        if not item.name or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
