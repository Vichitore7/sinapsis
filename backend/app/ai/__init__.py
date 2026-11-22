"""Capa de IA intercambiable.

Para cambiar de proveedor solo se implementa `AIProvider.reply` en un archivo
nuevo y se registra en `get_provider`. El resto del sistema no cambia.

Variables de entorno:
  THINKLOOP_AI_PROVIDER = mock (por defecto, $0, sin internet) | claude
  THINKLOOP_AI_MODEL    = modelo a usar (claude: claude-opus-5-5 por defecto)
  ANTHROPIC_API_KEY     = clave (solo en el backend, nunca en el navegador)
"""
from __future__ import annotations

import os
from functools import lru_cache

from .base import AIProvider, AIReply, TutorContext


@lru_cache(maxsize=1)
def get_provider() -> AIProvider:
    name = os.environ.get("THINKLOOP_AI_PROVIDER", "mock").lower()
    if name == "claude":
        from .claude_provider import ClaudeProvider
        return ClaudeProvider(model=os.environ.get("THINKLOOP_AI_MODEL", "claude-opus-5-5"))
    from .mock_provider import MockProvider
    return MockProvider()


__all__ = ["AIProvider", "AIReply", "TutorContext", "get_provider"]
