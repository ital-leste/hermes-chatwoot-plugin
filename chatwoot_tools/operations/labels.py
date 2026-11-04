from __future__ import annotations
from typing import Any


def modify(cw: Any, aid: int, cid: int, labels: list[str], *, remove: bool):
    op = cw.conversation_labels.remove if remove else cw.conversation_labels.add
    return op(aid, cid, labels)
