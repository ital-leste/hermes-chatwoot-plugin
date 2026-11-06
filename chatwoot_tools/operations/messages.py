from __future__ import annotations
from collections.abc import Mapping
from typing import Any

from ..errors import MediaUnavailableError, MediaRedirectRejectedError, PaginationError


def list_messages(cw: Any, aid: int, cid: int, before=None, after=None):
    kw = {k: v for k, v in {"before": before, "after": after}.items() if v is not None}
    return cw.messages.list(aid, cid, **kw)



# Contrato verificado em Chatwoot v4.19.0:
# MessageFinder#messages_between: id >= after AND id < before,
# ORDER BY created_at ASC, LIMIT 1000. Nunca inferir completude a partir
# de before=min(id) em pagina de messages_before, que ordena por created_at.
_CHATWOOT_ID_MAX = 2_147_483_647
_INTERVAL_LIMIT = 1000
_MAX_QUERIES = 128
_MAX_MESSAGES = 100_000


def summarize_messages(cw: Any, aid: int, cid: int):
    """Consolida intervalos disjuntos de IDs sem depender da ordenacao temporal.

    Requer a semantica de messages_between do Chatwoot 4.19.0. Um intervalo
    com exatamente 1000 itens pode ter sido truncado e e subdividido; um
    intervalo com menos de 1000 e completo. Erros nunca produzem complete=true.
    """
    unique: dict[int, dict] = {}
    seen_count = 0
    queries = 0
    # (inclusive, exclusive); before > INT_MAX omite o limite superior
    # no MessageFinder v4.19.0 e inclui tambem id=INT_MAX.
    pending = [(0, _CHATWOOT_ID_MAX + 1)]
    while pending:
        if queries >= _MAX_QUERIES:
            raise PaginationError("Limite de consultas; contagem nao comprovada.")
        low, high = pending.pop()
        result = list_messages(cw, aid, cid, after=low, before=high)
        queries += 1
        if not isinstance(result, Mapping) or not isinstance(result.get("payload"), list):
            raise PaginationError("Envelope de pagina invalido; contagem nao comprovada.")
        entries = result["payload"]
        if len(entries) > _INTERVAL_LIMIT:
            raise PaginationError("Limite da API alterado; contagem nao comprovada.")
        for item in entries:
            if not isinstance(item, Mapping) or type(item.get("id")) is not int:
                raise PaginationError("Mensagem sem ID valido; contagem nao comprovada.")
            mid = item["id"]
            if not low <= mid < high or mid <= 0 or mid > _CHATWOOT_ID_MAX:
                raise PaginationError("API ignorou intervalo de IDs; contagem nao comprovada.")
        if len(entries) == _INTERVAL_LIMIT:
            if high - low <= 1:
                raise PaginationError("Intervalo saturado; contagem nao comprovada.")
            # Usa um ID observado como pivô: divide o conjunto saturado
            # sem percorrer dezenas de intervalos vazios no espaço INT32.
            observed = sorted(item["id"] for item in entries)
            middle = observed[len(observed) // 2]
            if middle <= low or middle >= high:
                middle = low + (high - low) // 2
            if middle <= low or middle >= high:
                raise PaginationError("Intervalo sem divisao segura.")
            pending.extend(((middle, high), (low, middle)))
            continue
        for item in entries:
            mid = item["id"]
            seen_count += 1
            unique.setdefault(mid, dict(item))
            if len(unique) > _MAX_MESSAGES:
                raise PaginationError("Historico acima do limite; contagem nao comprovada.")

    ids = sorted(unique)
    # created_at e fornecido em segundos pelo Chatwoot; sem campo em todos
    # os itens, nao inferir qual foi a mensagem cronologicamente primeira.
    has_timestamps = all(
        type(m.get("created_at")) is int and m["created_at"] >= 0
        for m in unique.values()
    )
    earliest = (
        min(unique, key=lambda mid: (unique[mid]["created_at"], mid))
        if ids and has_timestamps else None
    )
    return {
        "complete": True,
        "unique_count": len(ids),
        "duplicate_count": seen_count - len(ids),
        "pages_read": queries,
        "first_message_id": ids[0] if ids else None,
        "last_message_id": ids[-1] if ids else None,
        "first_chronological_id": earliest,
        "chronology_verified": has_timestamps,
        "message_ids": ids,
    }


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
