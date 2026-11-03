"""Handlers Hermes, sem dependência de contrato HTTP próprio."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .chatwoot_tools.service import ToolService


def handler_for(service: ToolService, tool_name: str) -> Callable[..., str]:
    def handler(params: dict[str, Any], **kwargs: Any) -> str:
        del kwargs  # Contexto do Hermes não é usado como autorização de destinatário.
        return service.execute(tool_name, params)

    handler.__name__ = f"handle_{tool_name}"
    return handler
