"""Verifica associações reais retornadas pelo Chatwoot."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from .errors import ScopeError


def conversation_identity(cw: Any, account_id: int, inbox_id: int, conversation_id: int) -> dict:
    conversation = cw.conversations.get(account_id, conversation_id)
    verify_conversation(conversation, account_id, inbox_id, conversation_id)
    return conversation


def verify_conversation(conv: Any, account_id: int, inbox_id: int, conversation_id: int | None = None) -> None:
    if not isinstance(conv, Mapping):
        raise ScopeError("Conversa retornada não é objeto.")
    if conversation_id is not None and (type(conv.get("id")) is not int or conv["id"] != conversation_id):
        raise ScopeError("conversation_id divergente.")
    if type(conv.get("inbox_id")) is not int or conv["inbox_id"] != inbox_id:
        raise ScopeError("inbox_id divergente.")
    if "account_id" in conv and (type(conv["account_id"]) is not int or conv["account_id"] != account_id):
        raise ScopeError("account_id divergente.")


def payload_items(raw: Any) -> tuple[list[dict], str]:
    """Retorna itens e forma conhecida; falha fechada em envelopes desconhecidos."""
    if isinstance(raw, list):
        if any(not isinstance(x, dict) for x in raw):
            raise ScopeError("Lista de recursos inválida.")
        return raw, "list"
    if not isinstance(raw, dict):
        raise ScopeError("Resposta de listagem desconhecida.")
    if isinstance(raw.get("payload"), list):
        items = raw["payload"]
        form = "payload"
    elif isinstance(raw.get("data"), dict) and isinstance(raw["data"].get("payload"), list):
        items = raw["data"]["payload"]
        form = "data.payload"
    else:
        raise ScopeError("Formato de listagem não reconhecido; verificar versão Chatwoot.")
    if any(not isinstance(x, dict) for x in items):
        raise ScopeError("Listagem contém itens inválidos.")
    return items, form


def filtered_items(raw: Any, allowed: list[dict], form: str) -> Any:
    """Preserva campos nativos de itens e envelope; restringe somente a inbox solicitada."""
    if form == "list":
        return allowed
    import copy
    result = copy.deepcopy(raw)
    if form == "payload":
        result["payload"] = allowed
    else:
        result["data"]["payload"] = allowed
    return result


def contact_view(raw: Any) -> dict:
    """Extrai visão de validação, sem alterar o envelope original."""
    if not isinstance(raw, dict):
        raise ScopeError("Detalhe de contato inválido.")
    if "payload" in raw:
        if set(raw).intersection({"id", "data"}) or not isinstance(raw["payload"], dict):
            raise ScopeError("Envelope de contato ambíguo.")
        return raw["payload"]
    if "data" in raw and isinstance(raw["data"], dict) and "payload" in raw["data"]:
        if "id" in raw or not isinstance(raw["data"]["payload"], dict):
            raise ScopeError("Envelope de contato ambíguo.")
        return raw["data"]["payload"]
    return raw


def _check_contact(raw: Any, account_id: int, contact_id: int) -> dict:
    contact = contact_view(raw)
    if type(contact.get("id")) is not int or contact["id"] != contact_id:
        raise ScopeError("Identidade do contato divergente.")
    if "account_id" in contact and (type(contact["account_id"]) is not int or contact["account_id"] != account_id):
        raise ScopeError("Conta do contato divergente.")
    return contact


def _history_matches(items: list[dict], account_id: int, inbox_id: int) -> bool:
    for item in items:
        if type(item.get("inbox_id")) is not int:
            raise ScopeError("Histórico com inbox_id inválido.")
        if "account_id" in item and (type(item["account_id"]) is not int or item["account_id"] != account_id):
            raise ScopeError("Histórico com account_id divergente.")
        if item["inbox_id"] == inbox_id:
            return True
    return False


def contact_identity(cw: Any, account_id: int, inbox_id: int, contact_id: int) -> dict:
    original = cw.contacts.get(account_id, contact_id)
    contact = _check_contact(original, account_id, contact_id)
    if associated_inbox(contact, inbox_id):
        return original
    conversations = cw.contacts.list_conversations(account_id, contact_id)
    items, _ = payload_items(conversations)
    if _history_matches(items, account_id, inbox_id):
        return original
    raise ScopeError("Contato não possui associação comprovada à inbox informada.")


def associated_inbox(contact: dict, inbox_id: int) -> bool:
    associations = contact.get("contact_inboxes")
    if not isinstance(associations, list):
        return False
    for item in associations:
        if not isinstance(item, dict):
            continue
        inbox = item.get("inbox")
        value = inbox.get("id") if isinstance(inbox, dict) else item.get("inbox_id")
        if type(value) is int and value == inbox_id:
            return True
    return False
