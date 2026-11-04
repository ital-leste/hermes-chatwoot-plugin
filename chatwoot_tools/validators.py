"""Valida identidades do Chatwoot sem projetar ou reescrever seus JSONs nativos."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import ScopeError


def _positive_id(value: object) -> bool:
    return type(value) is int and value > 0


def _account_consistent(resource: Mapping[str, Any], account_id: int) -> None:
    if "account_id" in resource and (
        not _positive_id(resource["account_id"]) or resource["account_id"] != account_id
    ):
        raise ScopeError("account_id divergente na resposta Chatwoot.")


def conversation_identity(cw: Any, account_id: int, inbox_id: int, conversation_id: int) -> dict:
    raw = cw.conversations.get(account_id, conversation_id)
    verify_conversation(raw, account_id, inbox_id, conversation_id)
    return raw


def verify_conversation(conv: Any, account_id: int, inbox_id: int, conversation_id: int | None = None) -> None:
    if not isinstance(conv, Mapping):
        raise ScopeError("Conversa retornada não é objeto.")
    if conversation_id is not None and (
        not _positive_id(conv.get("id")) or conv["id"] != conversation_id
    ):
        raise ScopeError("conversation_id divergente.")
    if not _positive_id(conv.get("inbox_id")) or conv["inbox_id"] != inbox_id:
        raise ScopeError("inbox_id divergente.")
    _account_consistent(conv, account_id)


def payload_items(raw: Any) -> tuple[list[dict], str]:
    """Reconhece apenas formatos conhecidos de listagem, sem achatar os dados."""
    if isinstance(raw, list):
        items, form = raw, "list"
    elif isinstance(raw, dict) and isinstance(raw.get("payload"), list):
        items, form = raw["payload"], "payload"
    elif (isinstance(raw, dict) and isinstance(raw.get("data"), dict)
          and isinstance(raw["data"].get("payload"), list)):
        items, form = raw["data"]["payload"], "data.payload"
    else:
        raise ScopeError("Formato de listagem não reconhecido; verificar versão Chatwoot.")
    if any(not isinstance(item, dict) for item in items):
        raise ScopeError("Listagem contém itens inválidos.")
    return items, form


def filtered_items(raw: Any, allowed: list[dict], form: str) -> Any:
    """Preserva itens e metadados nativos, excluindo apenas itens de outras inboxes."""
    if form == "list":
        return allowed
    import copy
    result = copy.deepcopy(raw)
    if form == "payload":
        result["payload"] = allowed
    elif form == "data.payload":
        result["data"]["payload"] = allowed
    else:
        raise ScopeError("Formato de listagem desconhecido.")
    return result


def contact_view(raw: Any) -> Mapping[str, Any]:
    """Extrai somente a visão para validação, preservando o envelope original.

    Suporta objeto direto e payload contato; payload.contact é aceito apenas
    como formato explicitamente conhecido pela implementação, sem busca recursiva.
    Envelopes com mais de uma identidade concorrente falham fechados.
    """
    if not isinstance(raw, Mapping):
        raise ScopeError("Contato retornado não é objeto.")
    if "payload" in raw and "data" in raw:
        raise ScopeError("Envelope de contato ambíguo ou inválido.")
    if "payload" not in raw and "data" not in raw:
        contact = raw
    else:
        if "id" in raw:
            raise ScopeError("Envelope de contato ambíguo ou inválido.")
        if "payload" in raw:
            payload = raw["payload"]
        else:
            data = raw["data"]
            if not isinstance(data, Mapping) or "payload" not in data or "id" in data:
                raise ScopeError("Envelope de contato ambíguo ou inválido.")
            payload = data["payload"]
        if not isinstance(payload, Mapping):
            raise ScopeError("Envelope de contato inválido.")
        if "contact" in payload:
            if "id" in payload or not isinstance(payload["contact"], Mapping):
                raise ScopeError("Envelope de contato ambíguo ou inválido.")
            contact = payload["contact"]
        else:
            contact = payload
    if not _positive_id(contact.get("id")):
        raise ScopeError("Identidade do contato inválida.")
    return contact


def verify_contact(raw: Any, account_id: int, contact_id: int) -> Mapping[str, Any]:
    contact = contact_view(raw)
    if contact["id"] != contact_id:
        raise ScopeError("Identidade do contato divergente.")
    _account_consistent(contact, account_id)
    return contact


def associated_inbox(contact: Mapping[str, Any], inbox_id: int, account_id: int | None = None) -> bool:
    """Confere a associação quando ela está expressamente presente no contato."""
    associations = contact.get("contact_inboxes")
    if not isinstance(associations, list):
        return False
    for item in associations:
        if not isinstance(item, Mapping):
            continue
        inbox = item.get("inbox")
        value = inbox.get("id") if isinstance(inbox, Mapping) else item.get("inbox_id")
        if _positive_id(value) and value == inbox_id:
            if account_id is not None:
                _account_consistent(item, account_id)
                if isinstance(inbox, Mapping):
                    _account_consistent(inbox, account_id)
            return True
    return False


def history_association(items: list[dict], account_id: int, inbox_id: int, contact_id: int) -> bool:
    """Usa apenas evidências diretas e coerentes retornadas pela rota do contato."""
    found = False
    for conv in items:
        if type(conv.get("inbox_id")) is not int or conv["inbox_id"] != inbox_id:
            continue
        _account_consistent(conv, account_id)
        if "contact_id" in conv and (
            not _positive_id(conv["contact_id"]) or conv["contact_id"] != contact_id
        ):
            raise ScopeError("Contato divergente no histórico da conversa.")
        found = True
    return found


def contact_identity(cw: Any, account_id: int, inbox_id: int, contact_id: int) -> dict:
    raw = cw.contacts.get(account_id, contact_id)
    contact = verify_contact(raw, account_id, contact_id)
    if associated_inbox(contact, inbox_id, account_id):
        return raw
    # Alguns detalhes não informam contact_inboxes; consultar o histórico do contato.
    history = cw.contacts.list_conversations(account_id, contact_id)
    items, _ = payload_items(history)
    if history_association(items, account_id, inbox_id, contact_id):
        return raw
    raise ScopeError("Contato não possui associação comprovada à inbox informada.")
