"""Fronteira nativa Hermes: somente parâmetros do esquema chegam ao serviço."""
from __future__ import annotations

from typing import Any
from .chatwoot_tools.service import ToolService


def handler_for(service: ToolService, name: str):
    def handler(params: dict[str, Any], **kwargs: Any) -> str:
        # O contexto de sessão não equivale a uma autorização de destinatário.
        return service.execute(name, params)

    handler.__name__ = f"handle_{name}"
    return handler
