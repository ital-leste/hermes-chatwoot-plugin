"""Contatos por inbox. O filtro técnico de inbox não é projeção de privacidade."""
from __future__ import annotations
from typing import Any
from ..validators import contact_identity, payload_items, filtered_items, associated_inbox


def get(cw: Any, aid: int, iid: int, contact_id: int):
    return contact_identity(cw, aid, iid, contact_id)


def list_conversations(cw: Any, aid: int, iid: int, contact_id: int):
    contact_identity(cw, aid, iid, contact_id)
    res = cw.contacts.list_conversations(aid, contact_id)
    items, shape = payload_items(res)
    # A conta já é imposta pela rota; filtrar por inbox, pois o contato pode estar em várias.
    matches = [i for i in items if i.get("inbox_id") == iid and i.get("account_id", aid) == aid]
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
        if associated_inbox(item, iid):
            valid.append(item)
            continue
        contact = cw.contacts.get(aid, contact_id)
        if associated_inbox(contact, iid):
            valid.append(item)
            continue
        history = cw.contacts.list_conversations(aid, contact_id)
        conversations, _ = payload_items(history)
        if any(c.get("inbox_id") == iid for c in conversations):
            valid.append(item)
    return filtered_items(res, valid, shape)


def update(cw: Any, aid: int, contact_id: int, fields: dict):
    from chatwoot_client import Contact
    return cw.contacts.update(aid, contact_id, Contact(**fields))
