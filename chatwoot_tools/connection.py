"""Conexão Chatwoot: valores recuperados apenas do escopo de segredos do perfil."""
from __future__ import annotations

from typing import Any
from .config import PluginConfig, Credential, _url
from .errors import CredentialsError


def resolve_secret(name: str) -> str | None:
    # A API do Hermes respeita o secret scope da sessão/perfil. Não ler .env diretamente.
    from agent.secret_scope import get_secret
    return get_secret(name)


def create_client(url: str, token: str) -> Any:
    from chatwoot_client import CWClient
    return CWClient(url, token)


def resolve_connection(config: PluginConfig, credential: Credential, secret_provider=resolve_secret) -> tuple[str, str]:
    """Resolve URL e token a cada chamada, sem cache e sem retorno ao modelo."""
    url = secret_provider(config.base_url_env)
    if not isinstance(url, str) or not url.strip():
        raise CredentialsError("URL Chatwoot indisponível no ambiente do perfil.")
    # Aplicar a validação de HTTPS/HTTP apenas após resolver a URL do perfil.
    valid_url = _url(url, config.allow_insecure_http)
    token = secret_provider(credential.token_env)
    if not isinstance(token, str) or not token.strip():
        raise CredentialsError("Credencial Chatwoot indisponível no ambiente do perfil.")
    return valid_url, token.strip()
