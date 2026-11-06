"""Configuração imutável, uma conexão por contexto Hermes, negação por padrão."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
import re
from ipaddress import ip_address
from urllib.parse import urlsplit

from .errors import ConfigurationError

OPERATIONS = frozenset({
    "conversation.read", "conversation.list", "messages.read", "messages.send_public",
    "messages.send_private", "messages.send_media", "conversation.status.update", "conversation.labels.add",
    "conversation.labels.remove", "contacts.search", "contacts.read",
    "contacts.conversations.read", "contacts.update",
})
WRITABLE_FIELDS = frozenset({
    "name", "phone_number", "email", "identifier", "blocked", "avatar_url",
    "additional_attributes", "custom_attributes",
})
_KEYS = frozenset({"base_url_env", "credentials", "allow_insecure_http", "allowed_operations", "writable_contact_fields", "media_allowed_hosts"})
_ENV_NAME = re.compile(r"[A-Z_][A-Z0-9_]{0,127}\Z")
_IDENTITY_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_CREDENTIAL_KEYS = frozenset({"token_env", "account_id"})


def _env_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ENV_NAME.fullmatch(value):
        raise ConfigurationError(f"{label} deve ser nome de variável de ambiente válido.")
    return value


@dataclass(frozen=True, slots=True)
class Credential:
    name: str
    token_env: str
    account_id: int


def _credentials(raw: object) -> Mapping[str, Credential]:
    if not isinstance(raw, Mapping) or not raw:
        raise ConfigurationError("credentials deve conter ao menos uma identidade autorizada.")
    entries = {}
    used_env_names = set()
    for name, value in raw.items():
        if not isinstance(name, str) or not _IDENTITY_NAME.fullmatch(name):
            raise ConfigurationError("Nome de identidade inválido em credentials.")
        if not isinstance(value, Mapping) or set(value) - _CREDENTIAL_KEYS:
            raise ConfigurationError("Credencial contém campos desconhecidos ou formato inválido.")
        env_name = _env_name(value.get("token_env"), f"token_env de {name}")
        account_id = value.get("account_id")
        if type(account_id) is not int or account_id <= 0:
            raise ConfigurationError("account_id da credencial deve ser um inteiro positivo.")
        if env_name in used_env_names:
            raise ConfigurationError("Duas identidades não podem referenciar o mesmo token_env.")
        entries[name] = Credential(name, env_name, account_id)
        used_env_names.add(env_name)
    return MappingProxyType(entries)



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
    base_url_env: str
    credentials: Mapping[str, Credential]
    allow_insecure_http: bool
    operations: frozenset[str]
    writable_fields: frozenset[str]
    media_allowed_hosts: frozenset[str]


def parse_config(raw: object) -> PluginConfig:
    if not isinstance(raw, Mapping):
        raise ConfigurationError("Configuração deve ser um objeto.")
    if set(raw) - _KEYS:
        raise ConfigurationError("Configuração contém chave não reconhecida.")
    allow = raw.get("allow_insecure_http", False)
    if type(allow) is not bool:
        raise ConfigurationError("allow_insecure_http deve ser booleano.")
    url_env = _env_name(raw.get("base_url_env"), "base_url_env")
    credentials = _credentials(raw.get("credentials"))
    if url_env in {credential.token_env for credential in credentials.values()}:
        raise ConfigurationError("base_url_env não pode ser igual a token_env.")
    ops = _flags(raw.get("allowed_operations", {}), OPERATIONS, "allowed_operations")
    fields = _flags(raw.get("writable_contact_fields", {}), WRITABLE_FIELDS, "writable_contact_fields")
    hosts = raw.get("media_allowed_hosts", [])
    if (not isinstance(hosts, (list, tuple)) or
            any(not isinstance(host, str) or
                host != host.lower() or not re.fullmatch(
                    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*", host
                ) or "." not in host for host in hosts) or
            len(set(hosts)) != len(hosts)):
        raise ConfigurationError("media_allowed_hosts deve conter hostnames DNS explicitos sem wildcards.")
    for host in hosts:
        try:
            ip_address(host)
        except ValueError:
            if host.endswith((".localhost", ".local", ".internal")):
                raise ConfigurationError("Hostname local nao autorizado para midia.")
        else:
            raise ConfigurationError("Endereco IP literal nao autorizado para midia.")
    return PluginConfig(url_env, credentials, allow, ops, fields, frozenset(hosts))
