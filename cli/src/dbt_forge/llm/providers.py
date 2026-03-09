"""LLM provider implementations."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from dbt_forge.llm.base import GeneratedDescription, LLMProvider
from dbt_forge.llm.prompts import build_description_prompt, parse_description_response


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model
        if not self._api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY or pass api_key.")

    def name(self) -> str:
        return "Claude"

    def generate_descriptions(
        self,
        model_name: str,
        sql: str,
        columns: list[str],
        existing_descriptions: dict[str, str] | None = None,
    ) -> GeneratedDescription:
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        prompt = build_description_prompt(model_name, sql, columns, existing_descriptions)

        message = client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        return parse_description_response(model_name, response_text)


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        if not self._api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY or pass api_key.")

    def name(self) -> str:
        return "OpenAI"

    def generate_descriptions(
        self,
        model_name: str,
        sql: str,
        columns: list[str],
        existing_descriptions: dict[str, str] | None = None,
    ) -> GeneratedDescription:
        import openai

        client = openai.OpenAI(api_key=self._api_key)
        prompt = build_description_prompt(model_name, sql, columns, existing_descriptions)

        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )

        response_text = response.choices[0].message.content
        return parse_description_response(model_name, response_text)


class OllamaProvider(LLMProvider):
    """Ollama provider -- uses stdlib HTTP, no extra deps."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")

    def name(self) -> str:
        return f"Ollama ({self._model})"

    def generate_descriptions(
        self,
        model_name: str,
        sql: str,
        columns: list[str],
        existing_descriptions: dict[str, str] | None = None,
    ) -> GeneratedDescription:
        prompt = build_description_prompt(model_name, sql, columns, existing_descriptions)
        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode()

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                response_text = data.get("response", "")
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Could not connect to Ollama at {self._base_url}. Is Ollama running? Error: {e}"
            ) from e

        return parse_description_response(model_name, response_text)


def get_available_providers() -> list[tuple[str, str]]:
    """Return list of (provider_key, display_name) for available providers."""
    providers = []

    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append(("claude", "Claude (Anthropic)"))

    if os.environ.get("OPENAI_API_KEY"):
        providers.append(("openai", "OpenAI"))

    # Check if Ollama is running
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                providers.append(("ollama", "Ollama (local)"))
    except Exception:
        pass

    return providers


def create_provider(key: str) -> LLMProvider:
    """Create a provider instance by key."""
    if key == "claude":
        return ClaudeProvider()
    elif key == "openai":
        return OpenAIProvider()
    elif key == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown provider: {key}. Options: claude, openai, ollama")
