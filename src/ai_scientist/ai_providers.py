from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass


@dataclass
class ProviderResult:
    text: str
    provider: str
    warnings: list[str]


class AIProvider:
    name = "deterministic"

    def synthesize(self, prompt: str) -> ProviderResult:
        return ProviderResult(text="", provider=self.name, warnings=[])


class DeterministicProvider(AIProvider):
    name = "deterministic"


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, model: str):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def synthesize(self, prompt: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(text="", provider="deterministic", warnings=["OpenAI requested but OPENAI_API_KEY is missing; used deterministic fallback."])
        try:
            payload = json.dumps(
                {
                    "model": self.model,
                    "input": prompt,
                    "max_output_tokens": 600,
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("output_text") or ""
            return ProviderResult(text=text, provider=self.name, warnings=[])
        except Exception as exc:
            return ProviderResult(text="", provider="deterministic", warnings=[f"OpenAI provider failed; used deterministic fallback: {exc}"])


def build_provider(provider_name: str, model: str) -> AIProvider:
    if provider_name == "openai":
        return OpenAIProvider(model=model)
    return DeterministicProvider()
