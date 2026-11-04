"""Allowlist declarativa, sem autorização implícita."""
from __future__ import annotations
from collections.abc import Mapping
from .config import PluginConfig
from .errors import AuthorizationError


def require_operation(config: PluginConfig, op: str) -> None:
    if op not in config.operations:
        raise AuthorizationError("Operação não autorizada no perfil.")


def require_fields(config: PluginConfig, fields: Mapping[str, object]) -> None:
    if not fields or any(field not in config.writable_fields for field in fields):
        raise AuthorizationError("Campo de contato não autorizado ou atualização vazia.")
