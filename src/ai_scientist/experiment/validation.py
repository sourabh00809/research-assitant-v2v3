from __future__ import annotations


SNIPPETS = {
    "bootstrap_ci": """
def bootstrap_ci(values, iterations=1000, alpha=0.05, seed=13):
    import random
    values = list(values)
    rng = random.Random(seed)
    means = []
    for _ in range(iterations):
        sample = [rng.choice(values) for _ in values]
        means.append(sum(sample) / max(len(sample), 1))
    means.sort()
    lo = means[int((alpha / 2) * len(means))]
    hi = means[int((1 - alpha / 2) * len(means)) - 1]
    return lo, hi
""",
    "normal_ci": """
def normal_ci(values, z=1.96):
    import math
    values = list(values)
    mean = sum(values) / max(len(values), 1)
    variance = sum((x - mean) ** 2 for x in values) / max(len(values) - 1, 1)
    half_width = z * math.sqrt(variance / max(len(values), 1))
    return mean - half_width, mean + half_width
""",
    "paired_t_test": """
def paired_t_test(a, b):
    from statistics import mean
    diffs = [x - y for x, y in zip(a, b)]
    return {"mean_difference": mean(diffs) if diffs else 0.0, "note": "Use scipy.stats.ttest_rel when scipy is available."}
""",
    "wilcoxon": """
def wilcoxon_test(a, b):
    return {"note": "Use scipy.stats.wilcoxon(a, b) for non-parametric paired comparisons."}
""",
    "anova": """
def anova_test(*groups):
    return {"groups": len(groups), "note": "Use scipy.stats.f_oneway(*groups) when scipy is available."}
""",
    "mcnemar": """
def mcnemar_test(table):
    b = table[0][1]
    c = table[1][0]
    statistic = ((abs(b - c) - 1) ** 2) / max(b + c, 1)
    return {"chi_square": statistic}
""",
    "bonferroni": """
def bonferroni(p_values):
    p_values = list(p_values)
    return [min(p * len(p_values), 1.0) for p in p_values]
""",
    "fdr": """
def fdr_bh(p_values):
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    n = len(indexed)
    adjusted = [0.0] * n
    prev = 1.0
    for rank, (idx, p) in reversed(list(enumerate(indexed, start=1))):
        value = min(prev, p * n / rank)
        adjusted[idx] = value
        prev = value
    return adjusted
""",
}


def validation_snippets(tests: list[str] | None = None, confidence_interval: str | None = None, correction: str | None = None) -> dict[str, str]:
    selected = set(tests or ["paired_t_test"])
    if confidence_interval == "normal":
        selected.add("normal_ci")
    else:
        selected.add("bootstrap_ci")
    if correction:
        selected.add(correction)
    return {name: SNIPPETS[name].strip() for name in selected if name in SNIPPETS}
