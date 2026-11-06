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


def send_media(cw: Any, aid: int, cid: int, prepared, *, allowed_hosts: frozenset[str]):
    # O SDK resolve o HTTPS em cliente distinto, sem carregar token Chatwoot.
    return cw.messages.send_media(
        aid, cid, prepared, max_bytes=100_000_000,
        url_timeout=120.0, allowed_hosts=allowed_hosts,
    )
