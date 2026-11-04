"""Operações de contato restritas à inbox, mantendo JSON nativo dos itens permitidos."""
from __future__ import annotations
from typing import Any

from ..errors import ScopeError
from ..validators import (
    _account_consistent, _positive_id, associated_inbox, contact_identity,
    filtered_items, history_association, payload_items, verify_contact,
)


def get(cw: Any, aid: int, iid: int, contact_id: int):
    return contact_identity(cw, aid, iid, contact_id)


def list_conversations(cw: Any, aid: int, iid: int, contact_id: int):
    contact_identity(cw, aid, iid, contact_id)
    raw = cw.contacts.list_conversations(aid, contact_id)
    items, form = payload_items(raw)
    allowed = []
    for conv in items:
        if type(conv.get("inbox_id")) is not int or conv["inbox_id"] != iid:
            continue
        _account_consistent(conv, aid)
        if "contact_id" in conv and (
            not _positive_id(conv["contact_id"]) or conv["contact_id"] != contact_id
        ):
            raise ScopeError("Contato divergente no histórico da conversa.")
        allowed.append(conv)
    return filtered_items(raw, allowed, form)


def search(cw: Any, aid: int, iid: int, q: str, page: int | None = None):
    args = {"q": q}
    if page is not None:
        args["page"] = page
    raw = cw.contacts.search(aid, **args)
    items, form = payload_items(raw)
    allowed = []
    for candidate in items:
        cid = candidate.get("id")
        if not _positive_id(cid):
            raise ScopeError("Busca retornou contato sem identidade válida.")
        _account_consistent(candidate, aid)
        if associated_inbox(candidate, iid, aid):
            allowed.append(candidate)
            continue
        detail = cw.contacts.get(aid, cid)
        contact = verify_contact(detail, aid, cid)
        if associated_inbox(contact, iid, aid):
            allowed.append(candidate)
            continue
        history = cw.contacts.list_conversations(aid, cid)
        conversations, _ = payload_items(history)
        if history_association(conversations, aid, iid, cid):
            allowed.append(candidate)
    return filtered_items(raw, allowed, form)


def update(cw: Any, aid: int, contact_id: int, contact: Any):
    """Recebe Contact previamente validado antes da tentativa de escrita."""
    return cw.contacts.update(aid, contact_id, contact)
