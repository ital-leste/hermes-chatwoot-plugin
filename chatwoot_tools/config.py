"""Configuração estrita por instalação; ausências e campos desconhecidos falham fechados."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit
import re

from .errors import ConfigurationError


OPERATIONS = frozenset({
    "conversation.read",
    "messages.read",
    "messages.send_public",
    "messages.send_private",
    "conversation.status.update",
    "conversation.labels.add",
    "conversation.labels.remove",
})

_ALIAS = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_ENV = re.compile(r"[A-Z_][A-Z0-9_]{0,127}\Z")
_INSTALLATION_KEYS = frozenset({
    "base_url", "token_env", "allowed_account_ids", "allowed_inbox_ids",
    "allowed_operations",
})


def _ids(value: object, name: str, *, allow_empty: bool) -> frozenset[int]:
    if not isinstance(value, list):
        raise ConfigurationError(f"{name} deve ser lista de inteiros positivos.")
    if not allow_empty and not value:
        raise ConfigurationError(f"{name} não pode ser vazia.")
    if any(type(i) is not int or i <= 0 for i in value):
        raise ConfigurationError(f"{name} contém identificador inválido.")
    if len(set(value)) != len(value):
        raise ConfigurationError(f"{name} contém identificadores duplicados.")
    return frozenset(value)


def _url(base_url: object) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise ConfigurationError("base_url obrigatória e textual.")
    value = base_url.strip().rstrip("/")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as exc:
        raise ConfigurationError("base_url inválida.") from exc
    if (parts.scheme not in {"http", "https"} or not parts.hostname
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or port == 0):
        raise ConfigurationError("base_url deve ser endereço http(s) válido, sem credenciais ou query.")
    return value


@dataclass(frozen=True, slots=True)
class Installation:
    alias: str
    base_url: str
    token_env: str
    account_ids: frozenset[int]
    inbox_ids: frozenset[int] | None
    operations: frozenset[str]


def parse_installations(raw: object) -> Mapping[str, Installation]:
    """Valida o mapa inteiro para impedir configurações parcialmente aceitas."""
    if not isinstance(raw, Mapping) or not raw:
        raise ConfigurationError("installations deve conter ao menos uma instalação.")
    parsed: dict[str, Installation] = {}
    for alias, data in raw.items():
        if not isinstance(alias, str) or not _ALIAS.fullmatch(alias):
            raise ConfigurationError("Alias de instalação inválido.")
        if not isinstance(data, Mapping):
            raise ConfigurationError(f"Instalação '{alias}' deve ser objeto.")
        unknown = set(data) - _INSTALLATION_KEYS
        if unknown:
            raise ConfigurationError(f"Instalação '{alias}' contém chaves não reconhecidas.")
        base_url = _url(data.get("base_url"))
        token_env = data.get("token_env")
        if not isinstance(token_env, str) or not _ENV.fullmatch(token_env):
            raise ConfigurationError("token_env deve ser nome válido de variável de ambiente.")
        account_ids = _ids(data.get("allowed_account_ids"), "allowed_account_ids", allow_empty=False)
        inbox_ids = (
            None if "allowed_inbox_ids" not in data else
            _ids(data["allowed_inbox_ids"], "allowed_inbox_ids", allow_empty=True)
        )
        operations_raw = data.get("allowed_operations", {})
        if not isinstance(operations_raw, Mapping):
            raise ConfigurationError("allowed_operations deve ser objeto de operação: booleano.")
        if any(not isinstance(key, str) or key not in OPERATIONS for key in operations_raw):
            raise ConfigurationError("allowed_operations contém nome desconhecido.")
        if any(type(value) is not bool for value in operations_raw.values()):
            raise ConfigurationError("allowed_operations aceita somente true/false.")
        ops = frozenset(op for op, enabled in operations_raw.items() if enabled)
        parsed[alias] = Installation(alias, base_url, token_env, account_ids, inbox_ids, ops)
    return MappingProxyType(parsed)
