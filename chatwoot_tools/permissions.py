"""Autorização específica do plugin, independente das permissões do token Chatwoot."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import Installation
from .errors import AuthorizationError, ScopeError


def authorize(installation: Installation, operation: str, account_id: int) -> None:
    if operation not in installation.operations:
        raise AuthorizationError("Operação não autorizada nesta instalação.")
    if account_id not in installation.account_ids:
        raise ScopeError("Conta fora do escopo autorizado.")


def verify_conversation(
    conversation: Any, *, account_id: int, conversation_id: int, installation: Installation,
) -> dict[str, Any]:
    if not isinstance(conversation, dict):
        raise ScopeError("A conversa não retornou um objeto válido.")
    if type(conversation.get("id")) is not int or conversation["id"] != conversation_id:
        raise ScopeError("Identidade da conversa não confirmada.")
    if "account_id" in conversation and (
        type(conversation["account_id"]) is not int or conversation["account_id"] != account_id
    ):
        raise ScopeError("Conta retornada diverge da conta solicitada.")
    if installation.inbox_ids is not None:
        inbox_id = conversation.get("inbox_id")
        if type(inbox_id) is not int or inbox_id not in installation.inbox_ids:
            raise ScopeError("Inbox fora do escopo autorizado.")
    return conversation
