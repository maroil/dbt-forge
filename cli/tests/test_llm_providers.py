"""Tests for LLM provider abstraction."""

from __future__ import annotations

import json

import pytest

from dbt_forge.llm.base import GeneratedDescription
from dbt_forge.llm.prompts import build_description_prompt, parse_description_response
from dbt_forge.llm.providers import create_provider, get_available_providers


class TestGeneratedDescription:
    def test_defaults(self):
        desc = GeneratedDescription(model_name="test")
        assert desc.model_description == ""
        assert desc.column_descriptions == {}


class TestBuildPrompt:
    def test_basic_prompt(self):
        prompt = build_description_prompt(
            "stg_orders",
            "SELECT id, amount FROM raw.orders",
            ["id", "amount"],
        )
        assert "stg_orders" in prompt
        assert "SELECT id, amount" in prompt
        assert "id" in prompt
        assert "amount" in prompt
        assert "JSON" in prompt

    def test_with_existing_descriptions(self):
        prompt = build_description_prompt(
            "stg_orders",
            "SELECT id FROM raw.orders",
            ["id"],
            existing_descriptions={"id": "Primary key"},
        )
        assert "Primary key" in prompt
        assert "Existing descriptions" in prompt


class TestParseResponse:
    def test_valid_json(self):
        response = json.dumps(
            {
                "model_description": "Orders staging model",
                "columns": {
                    "id": "Primary key",
                    "amount": "Order total",
                },
            }
        )
        result = parse_description_response("stg_orders", response)
        assert result.model_name == "stg_orders"
        assert result.model_description == "Orders staging model"
        assert result.column_descriptions["id"] == "Primary key"
        assert result.column_descriptions["amount"] == "Order total"

    def test_json_in_markdown_fences(self):
        response = '```json\n{"model_description": "Test", "columns": {}}\n```'
        result = parse_description_response("test", response)
        assert result.model_description == "Test"

    def test_invalid_json(self):
        result = parse_description_response("test", "not json at all")
        assert result.model_name == "test"
        assert result.model_description == ""
        assert result.column_descriptions == {}

    def test_json_embedded_in_text(self):
        response = (
            "Here are the descriptions:\n"
            '{"model_description": "Test model", "columns": {"id": "PK"}}\n'
            "Done!"
        )
        result = parse_description_response("test", response)
        assert result.model_description == "Test model"
        assert result.column_descriptions["id"] == "PK"

    def test_empty_response(self):
        result = parse_description_response("test", "")
        assert result.model_description == ""


class TestGetAvailableProviders:
    def test_no_providers(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Ollama won't be running in test
        providers = get_available_providers()
        # May be empty or just ollama if running locally
        for key, name in providers:
            assert key in ("claude", "openai", "ollama")

    def test_claude_available(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        providers = get_available_providers()
        keys = [k for k, _ in providers]
        assert "claude" in keys

    def test_openai_available(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        providers = get_available_providers()
        keys = [k for k, _ in providers]
        assert "openai" in keys


class TestCreateProvider:
    def test_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("unknown")

    def test_claude_missing_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="API key required"):
            create_provider("claude")

    def test_openai_missing_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="API key required"):
            create_provider("openai")

    def test_ollama_creates(self):
        provider = create_provider("ollama")
        assert provider.name().startswith("Ollama")
