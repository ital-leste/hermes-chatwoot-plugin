"""Contatos por inbox. O filtro técnico de inbox não é projeção de privacidade."""
from __future__ import annotations
from typing import Any
from ..validators import contact_identity, contact_view, _check_contact, _history_matches, payload_items, filtered_items, associated_inbox


def get(cw: Any, aid: int, iid: int, contact_id: int):
    return contact_identity(cw, aid, iid, contact_id)


def list_conversations(cw: Any, aid: int, iid: int, contact_id: int):
    contact_identity(cw, aid, iid, contact_id)
    res = cw.contacts.list_conversations(aid, contact_id)
    items, shape = payload_items(res)
    # A conta já é imposta pela rota; filtrar por inbox, pois o contato pode estar em várias.
    matches = []
    for item in items:
        if type(item.get("inbox_id")) is not int:
            from ..errors import ScopeError
            raise ScopeError("Histórico com inbox_id inválido.")
        if "account_id" in item and (type(item["account_id"]) is not int or item["account_id"] != aid):
            from ..errors import ScopeError
            raise ScopeError("Histórico com account_id divergente.")
        if item["inbox_id"] == iid:
            matches.append(item)
    return filtered_items(res, matches, shape)


def search(cw: Any, aid: int, iid: int, q: str, page: int | None = None):
    kw = {"q":q}
    if page is not None:
        kw["page"] = page
    res = cw.contacts.search(aid, **kw)
    items, shape = payload_items(res)
    # Para cada candidato exigir prova de associação real à inbox, evitando
    # devolver contatos de outras inboxes apenas porque o nome coincide.
    valid = []
    for item in items:
        contact_id = item.get("id")
        if type(contact_id) is not int or contact_id <= 0:
            from ..errors import ScopeError
            raise ScopeError("Busca retornou contato sem identidade válida.")
        _check_contact(item, aid, contact_id)
        if associated_inbox(item, iid):
            valid.append(item)
            continue
        detail = cw.contacts.get(aid, contact_id)
        checked = _check_contact(detail, aid, contact_id)
        if associated_inbox(checked, iid):
            valid.append(item)
            continue
        history = cw.contacts.list_conversations(aid, contact_id)
        conversations, _ = payload_items(history)
        if _history_matches(conversations, aid, iid):
            valid.append(item)
    return filtered_items(res, valid, shape)


def update(cw: Any, aid: int, contact_id: int, fields: dict):
    from chatwoot_client import Contact
    return cw.contacts.update(aid, contact_id, Contact(**fields))
