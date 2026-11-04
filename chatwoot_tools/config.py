"""Configuração imutável, uma conexão por contexto Hermes, negação por padrão."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlsplit

from .errors import ConfigurationError

OPERATIONS = frozenset({
    "conversation.read", "conversation.list", "messages.read", "messages.send_public",
    "messages.send_private", "conversation.status.update", "conversation.labels.add",
    "conversation.labels.remove", "contacts.search", "contacts.read",
    "contacts.conversations.read", "contacts.update",
})
WRITABLE_FIELDS = frozenset({
    "name", "phone_number", "email", "identifier", "blocked", "avatar_url",
    "additional_attributes", "custom_attributes",
})
_KEYS = frozenset({"base_url", "allow_insecure_http", "allowed_operations", "writable_contact_fields"})


def _url(value: object, allow_http: bool) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("base_url deve ser texto não vazio.")
    value = value.strip().rstrip("/")
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as exc:
        raise ConfigurationError("base_url inválida.") from exc
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConfigurationError("base_url deve ter esquema HTTP(S) e host válido, sem credenciais, query ou fragmento.")
    if parsed.scheme == "http" and not allow_http:
        host = parsed.hostname.lower()
        try:
            local = ip_address(host).is_loopback
        except ValueError:
            local = host == "localhost"
        if not local:
            raise ConfigurationError("HTTPS obrigatório fora de loopback; exceção explícita necessária.")
    return value


def _flags(raw: object, allowed: frozenset[str], name: str) -> frozenset[str]:
    if not isinstance(raw, Mapping):
        raise ConfigurationError(f"{name} deve ser um objeto de chaves booleanas.")
    if any(not isinstance(k, str) or k not in allowed for k in raw):
        raise ConfigurationError(f"{name} contém chave não reconhecida.")
    if any(type(v) is not bool for v in raw.values()):
        raise ConfigurationError(f"{name} aceita somente true ou false.")
    return frozenset(k for k, v in raw.items() if v)


@dataclass(frozen=True, slots=True)
class PluginConfig:
    base_url: str
    operations: frozenset[str]
    writable_fields: frozenset[str]


def parse_config(raw: object) -> PluginConfig:
    if not isinstance(raw, Mapping):
        raise ConfigurationError("Configuração deve ser um objeto.")
    if set(raw) - _KEYS:
        raise ConfigurationError("Configuração contém chave não reconhecida.")
    allow = raw.get("allow_insecure_http", False)
    if type(allow) is not bool:
        raise ConfigurationError("allow_insecure_http deve ser booleano.")
    url = _url(raw.get("base_url"), allow)
    ops = _flags(raw.get("allowed_operations", {}), OPERATIONS, "allowed_operations")
    fields = _flags(raw.get("writable_contact_fields", {}), WRITABLE_FIELDS, "writable_contact_fields")
    return PluginConfig(url, ops, fields)
