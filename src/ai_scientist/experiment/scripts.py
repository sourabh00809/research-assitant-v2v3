from __future__ import annotations

from ..models import ExperimentPlan
from .validation import validation_snippets


def generate_script(plan: ExperimentPlan) -> str:
    datasets = [name_of(item) for item in plan.datasets]
    baselines = [name_of(item) for item in plan.baselines]
    metrics = [name_of(item) for item in plan.metrics]
    snippets = validation_snippets(
        plan.validation_plan.statistical_tests,
        plan.validation_plan.confidence_interval,
        plan.validation_plan.correction,
    )
    body = render_with_jinja(plan, datasets, baselines, metrics, snippets) or deterministic_script(plan, datasets, baselines, metrics, snippets)
    try:
        import black  # type: ignore

        body = black.format_str(body, mode=black.FileMode())
    except Exception:
        compile(body, f"{plan.id}.py", "exec")
    return body


def render_with_jinja(plan: ExperimentPlan, datasets: list[str], baselines: list[str], metrics: list[str], snippets: dict[str, str]) -> str:
    try:
        from jinja2 import Template  # type: ignore

        template = Template(SCRIPT_TEMPLATE)
        return template.render(plan=plan, datasets=repr(datasets), baselines=repr(baselines), metrics=repr(metrics), snippets=snippets)
    except Exception:
        return ""


def deterministic_script(plan: ExperimentPlan, datasets: list[str], baselines: list[str], metrics: list[str], snippets: dict[str, str]) -> str:
    snippet_text = "\n\n".join(snippets.values())
    return f'''"""Generated evaluation script for {plan.title}.

Fill in dataset loading and model execution for your environment, then run:
    python generated_experiment.py
"""

from __future__ import annotations

import json
from statistics import mean, pstdev

DATASETS = {datasets!r}
BASELINES = {baselines!r}
METRICS = {metrics!r}
CV_FOLDS = 5
BOOTSTRAP_ITERATIONS = 1000


def load_dataset(name):
    """Return examples for a dataset. Replace with real loading code."""
    return [{{"input": "example", "label": 1, "dataset": name}}]


def evaluate_baseline(model_name, examples):
    """Replace this deterministic placeholder with real model inference."""
    scores = []
    for index, _example in enumerate(examples):
        scores.append(0.70 + (index % 3) * 0.02)
    return scores


def summarize_scores(scores):
    return {{
        "mean": round(mean(scores), 4) if scores else 0.0,
        "std": round(pstdev(scores), 4) if len(scores) > 1 else 0.0,
        "n": len(scores),
    }}


{snippet_text}


def main():
    results = {{}}
    for dataset in DATASETS:
        examples = load_dataset(dataset)
        results[dataset] = {{}}
        for baseline in BASELINES:
            scores = evaluate_baseline(baseline, examples)
            results[dataset][baseline] = summarize_scores(scores)
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    main()
'''


def name_of(item) -> str:
    return item if isinstance(item, str) else item.name


SCRIPT_TEMPLATE = '''"""Generated evaluation script for {{ plan.title }}.

Fill in dataset loading and model execution for your environment, then run:
    python generated_experiment.py
"""

from __future__ import annotations

import json
from statistics import mean, pstdev

DATASETS = {{ datasets }}
BASELINES = {{ baselines }}
METRICS = {{ metrics }}
CV_FOLDS = 5
BOOTSTRAP_ITERATIONS = 1000


def load_dataset(name):
    """Return examples for a dataset. Replace with real loading code."""
    return [{"input": "example", "label": 1, "dataset": name}]


def evaluate_baseline(model_name, examples):
    """Replace this deterministic placeholder with real model inference."""
    scores = []
    for index, _example in enumerate(examples):
        scores.append(0.70 + (index % 3) * 0.02)
    return scores


def summarize_scores(scores):
    return {
        "mean": round(mean(scores), 4) if scores else 0.0,
        "std": round(pstdev(scores), 4) if len(scores) > 1 else 0.0,
        "n": len(scores),
    }


{% for snippet in snippets.values() %}
{{ snippet }}

{% endfor %}
def main():
    results = {}
    for dataset in DATASETS:
        examples = load_dataset(dataset)
        results[dataset] = {}
        for baseline in BASELINES:
            scores = evaluate_baseline(baseline, examples)
            results[dataset][baseline] = summarize_scores(scores)
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    main()
'''
