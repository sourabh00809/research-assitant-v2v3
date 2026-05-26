from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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

    def synthesize(self, prompt: str) -> ProviderResult:
        text = _deterministic_synthesis(prompt)
        return ProviderResult(text=text, provider=self.name, warnings=[])


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
                    "messages": [{"role": "user", "content": prompt}],
                    "max_completion_tokens": 2048,
                    "temperature": 0.3,
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            choices = data.get("choices", [])
            text = choices[0]["message"]["content"] if choices else ""
            return ProviderResult(text=text, provider=self.name, warnings=[])
        except Exception as exc:
            return ProviderResult(text="", provider="deterministic", warnings=[f"OpenAI provider failed; used deterministic fallback: {exc}"])


class HuggingFaceProvider(AIProvider):
    """Free inference via HuggingFace Inference API.

    Uses models like mistralai/Mistral-7B-Instruct-v0.3 or
    HuggingFaceH4/zephyr-7b-beta.  Requires a free HF token set via
    HUGGINGFACE_API_TOKEN env var (no-cost, just register at hf.co).
    """

    name = "huggingface"

    def __init__(self, model: str = "mistralai/Mistral-7B-Instruct-v0.3"):
        self.model = model
        self.api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")

    def synthesize(self, prompt: str) -> ProviderResult:
        if not self.api_token:
            return ProviderResult(text="", provider="deterministic", warnings=["HUGGINGFACE_API_TOKEN not set; used deterministic fallback."])
        try:
            payload = json.dumps({
                "inputs": prompt,
                "parameters": {"max_new_tokens": 1024, "temperature": 0.3, "return_full_text": False},
            }).encode("utf-8")
            request = urllib.request.Request(
                f"https://api-inference.huggingface.co/models/{self.model}",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0:
                text = data[0].get("generated_text", "")
            elif isinstance(data, dict):
                text = data.get("generated_text", "")
            else:
                text = ""
            if text:
                return ProviderResult(text=text, provider=self.name, warnings=[])
            return ProviderResult(text="", provider="deterministic", warnings=["HuggingFace returned empty response; used deterministic fallback."])
        except Exception as exc:
            return ProviderResult(text="", provider="deterministic", warnings=[f"HuggingFace provider failed; used deterministic fallback: {exc}"])


class GroqProvider(AIProvider):
    """Fast LLM inference via Groq API.

    Uses Mixtral, Llama 3, or Gemma models through Groq's ultra-fast
    inference engine.  Free tier allows 30 req/min.  Requires GROQ_API_KEY.
    """

    name = "groq"

    def __init__(self, model: str = "mixtral-8x7b-32768"):
        self.model = model
        self.api_key = os.getenv("GROQ_API_KEY", "")

    def synthesize(self, prompt: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(text="", provider="deterministic", warnings=["GROQ_API_KEY not set; used deterministic fallback."])
        try:
            payload = json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.3,
            }).encode("utf-8")
            request = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            choices = data.get("choices", [])
            text = choices[0]["message"]["content"] if choices else ""
            if text:
                return ProviderResult(text=text, provider=self.name, warnings=[])
            return ProviderResult(text="", provider="deterministic", warnings=["Groq returned empty response; used deterministic fallback."])
        except Exception as exc:
            return ProviderResult(text="", provider="deterministic", warnings=[f"Groq provider failed; used deterministic fallback: {exc}"])


class OllamaProvider(AIProvider):
    """Free local inference via Ollama.

    Connects to http://localhost:11434 by default.  Install Ollama from
    ollama.com, then `ollama pull mistral` (or any model).  No API key
    needed, runs on local GPU/CPU, completely free.
    """

    name = "ollama"

    def __init__(self, model: str = "mistral", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def synthesize(self, prompt: str) -> ProviderResult:
        try:
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 1024},
            }).encode("utf-8")
            request = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("response", "")
            if text:
                return ProviderResult(text=text, provider=self.name, warnings=[])
            return ProviderResult(text="", provider="deterministic", warnings=["Ollama returned empty response; used deterministic fallback."])
        except Exception as exc:
            return ProviderResult(text="", provider="deterministic", warnings=[f"Ollama provider failed; used deterministic fallback: {exc}"])


def _detect_ollama() -> bool:
    """Quick check if Ollama is reachable on localhost:11434."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return len(data.get("models", [])) > 0
    except Exception:
        return False


def build_provider(provider_name: str | None = None, model: str | None = None) -> AIProvider:
    if provider_name == "openai":
        return OpenAIProvider(model=model or "gpt-4.1-mini")
    if provider_name == "huggingface":
        return HuggingFaceProvider(model=model or "mistralai/Mistral-7B-Instruct-v0.3")
    if provider_name == "ollama":
        return OllamaProvider(model=model or "mistral")
    if provider_name == "groq":
        return GroqProvider(model=model or "mixtral-8x7b-32768")
    if provider_name and provider_name != "auto":
        return DeterministicProvider()

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        logger.info("AI provider: auto-selected Groq")
        return GroqProvider(model=model or "mixtral-8x7b-32768")
    if _detect_ollama():
        logger.info("AI provider: auto-detected Ollama")
        return OllamaProvider(model=model or "mistral")
    token = os.getenv("HUGGINGFACE_API_TOKEN")
    if token:
        logger.info("AI provider: auto-selected HuggingFace")
        return HuggingFaceProvider(model=model or "mistralai/Mistral-7B-Instruct-v0.3")
    logger.info("AI provider: no provider detected, using deterministic fallback")
    return DeterministicProvider()


def _deterministic_synthesis(prompt: str) -> str:
    prefix = "Synthesize research brief for: "
    question = prompt.replace(prefix, "").strip() if prefix in prompt else prompt[:120]
    return (
        f"Deterministic Synthesis for: {question}\n\n"
        f"Analysis of the provided context indicates the investigation centers on "
        f"'{question}'. Retrieved materials offer methodological grounding, though "
        f"full-text extraction and structured evidence are limited. Key themes include "
        f"representation learning, retrieval-augmented architectures, and benchmark-driven "
        f"evaluation.\n\n"
        f"Quality review notes that several sources lack explicit dataset citations, "
        f"baseline comparisons, or statistical validation. These gaps should be resolved "
        f"before drawing conclusions. Cross-referencing with existing project memory "
        f"suggests alignment with previously identified open problems.\n\n"
        f"Recommended next steps: (1) extract full text from top-ranked papers, "
        f"(2) design ablation experiments against identified baselines, and "
        f"(3) populate project memory with validated findings for future cycles."
    )
