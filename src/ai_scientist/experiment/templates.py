from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "experiment"


def list_templates() -> list[dict[str, Any]]:
    templates = []
    for path in sorted(TEMPLATE_DIR.glob("*.yaml")):
        template = load_template(path.stem)
        templates.append({k: template.get(k) for k in ["id", "domain", "task", "title"]})
    return templates


def load_template(template_id: str) -> dict[str, Any]:
    path = TEMPLATE_DIR / f"{template_id}.yaml"
    if not path.exists():
        raise KeyError(f"Template not found: {template_id}")
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
    except Exception:
        data = parse_simple_yaml(text)
    data.setdefault("id", template_id)
    data.setdefault("title", template_id.replace("_", " ").title())
    return data


def parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_key: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if not value:
                result[key] = []
            elif value.startswith("["):
                result[key] = json.loads(value.replace("'", '"'))
            else:
                result[key] = value.strip('"')
            continue
        if current_key and stripped.startswith("- "):
            value = stripped[2:].strip()
            if value.startswith("{"):
                value = json.loads(value.replace("'", '"'))
            result.setdefault(current_key, []).append(value.strip('"') if isinstance(value, str) else value)
    return result
