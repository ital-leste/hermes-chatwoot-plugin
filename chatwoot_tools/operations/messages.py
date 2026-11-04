from __future__ import annotations
from typing import Any


def list_messages(cw: Any, aid: int, cid: int, before=None, after=None):
    kw = {k: v for k, v in {"before": before, "after": after}.items() if v is not None}
    return cw.messages.list(aid, cid, **kw)


def send(cw: Any, aid: int, cid: int, content: str, private: bool, *, prepared=None):
    if prepared is None:
        from chatwoot_client import TextMessage
        prepared = TextMessage(content, private=private)
    return cw.messages.send_text(aid, cid, prepared)
