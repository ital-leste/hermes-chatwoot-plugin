from __future__ import annotations
from collections.abc import Mapping
from typing import Any

from ..errors import MediaUnavailableError, MediaRedirectRejectedError, PaginationError


def list_messages(cw: Any, aid: int, cid: int, before=None, after=None):
    kw = {k: v for k, v in {"before": before, "after": after}.items() if v is not None}
    return cw.messages.list(aid, cid, **kw)



def summarize_messages(cw: Any, aid: int, cid: int):
    """Conta IDs distintos em todas as paginas; nunca retorna total parcial como completo.

    Mantem list_messages como consulta crua de uma pagina. O resumo e um modo
    opt-in da mesma ferramenta, sem delegar a contagem ao LLM.
    """
    unique: dict[int, dict] = {}
    duplicates = 0
    before = None
    previous_min = None
    max_pages = 100
    for page in range(1, max_pages + 1):
        result = list_messages(cw, aid, cid, before=before)
        if not isinstance(result, Mapping) or not isinstance(result.get("payload"), list):
            raise PaginationError("Envelope de pagina invalido; contagem nao comprovada.")
        messages = result["payload"]
        if not messages:
            ids = sorted(unique)
            return {
                "complete": True, "unique_count": len(ids),
                "duplicate_count": duplicates, "pages_read": page,
                "first_message_id": ids[0] if ids else None,
                "last_message_id": ids[-1] if ids else None,
                "message_ids": ids,
            }
        current_ids = []
        for item in messages:
            if (not isinstance(item, Mapping)
                    or type(item.get("id")) is not int or item["id"] <= 0):
                raise PaginationError("Mensagem sem id valido; contagem nao comprovada.")
            message_id = item["id"]
            current_ids.append(message_id)
            if message_id in unique:
                duplicates += 1
            else:
                unique[message_id] = dict(item)
        cursor = min(current_ids)
        if previous_min is not None and cursor >= previous_min:
            raise PaginationError("Cursor sem progresso; contagem nao comprovada.")
        previous_min = before = cursor
    raise PaginationError("Limite de paginas atingido; contagem nao comprovada.")


def send(cw: Any, aid: int, cid: int, content: str, private: bool, *, prepared=None):
    if prepared is None:
        from chatwoot_client import TextMessage
        prepared = TextMessage(content, private=private)
    return cw.messages.send_text(aid, cid, prepared)


def send_media(cw: Any, aid: int, cid: int, prepared, *, allowed_hosts: frozenset[str]):
    # ErroAnexoChatwoot somente e lancado pela preparacao/download anterior
    # ao POST; o SDK nao o reutiliza para resultados incertos de escrita.
    from chatwoot_client import ErroAnexoChatwoot, ErroRedirecionamentoAnexoChatwoot
    try:
        return cw.messages.send_media(
            aid, cid, prepared, max_bytes=100_000_000,
            url_timeout=120.0, allowed_hosts=allowed_hosts,
        )
    except ErroRedirecionamentoAnexoChatwoot:
        raise MediaRedirectRejectedError(
            "Redirecionamento de midia rejeitado antes da escrita."
        ) from None
    except ErroAnexoChatwoot:
        raise MediaUnavailableError(
            "Midia inacessivel ou invalida antes da escrita."
        ) from None
