from __future__ import annotations
from typing import Any
from ..validators import conversation_identity, payload_items, verify_conversation


def get(cw: Any, aid: int, iid: int, cid: int):
    return conversation_identity(cw, aid, iid, cid)


def list_conversations(cw: Any, aid: int, iid: int, *, status=None, q=None, page=None):
    opts = {k:v for k,v in {"status":status, "q":q, "page":page}.items() if v is not None}
    result = cw.conversations.list(aid, inbox_id=iid, **opts)
    items, _ = payload_items(result)
    for item in items:
        verify_conversation(item, aid, iid)
    return result


def set_status(cw: Any, aid: int, cid: int, status: str, snoozed_until=None):
    from chatwoot_client import ConversationStatus
    kw = {"snoozed_until": snoozed_until} if snoozed_until is not None else {}
    return cw.conversations.set_status(aid, cid, ConversationStatus(status), **kw)
