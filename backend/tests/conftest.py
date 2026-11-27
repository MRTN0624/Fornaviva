"""Aislamiento: ninguna prueba usa dotenv local ni conexiones reales."""
import os

os.environ["PYTHON_DOTENV_DISABLED"] = "1"

import pytest


@pytest.fixture(autouse=True)
def aislar_proveedor(monkeypatch):
    from google.genai.models import AsyncModels

    async def prohibido(*args, **kwargs):
        raise AssertionError("Las pruebas deben simular Gemini; red prohibida")

    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("LLM_MODEL_NAME", raising=False)
    monkeypatch.setattr(AsyncModels, "generate_content", prohibido)
