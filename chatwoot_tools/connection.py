"""Conexão do perfil Hermes: nunca lê .env nem recebe token via tool call."""
from __future__ import annotations

from typing import Any
from .errors import CredentialsError

TOKEN_ENV = "CHATWOOT_API_TOKEN"


def resolve_secret(name: str) -> str | None:
    from agent.secret_scope import get_secret
    return get_secret(name)


def create_client(url: str, token: str) -> Any:
    from chatwoot_client import CWClient
    return CWClient(url, token)


def require_token(secret_provider=resolve_secret) -> str:
    value = secret_provider(TOKEN_ENV)
    if not isinstance(value, str) or not value.strip():
        raise CredentialsError("Token Chatwoot indisponível no perfil Hermes.")
    return value.strip()
