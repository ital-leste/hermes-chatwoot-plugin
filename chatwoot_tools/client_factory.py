"""Único ponto de construção do cliente Python externo."""
from __future__ import annotations

from typing import Any


def create_client(url: str, token: str) -> Any:
    from chatwoot_client import CWClient

    return CWClient(url, token)


def resolve_secret(name: str) -> str | None:
    # Interface pública documentada do Hermes; nunca ler arquivos privados.
    from agent.secret_scope import get_secret

    return get_secret(name)
