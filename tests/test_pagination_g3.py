"""G3: contagem integral por intervalos disjuntos na API Chatwoot 4.19.0.

O finder filtra por id mas ordena por created_at. Paginar so com
before=min(id) perde mensagens cujo timestamp diverge da ordem dos IDs.
"""
import json

from conftest import FakeClient


IDS = sorted([
    *range(127, 132), *range(142, 154), *range(155, 169),
])
ID_MAX = 2_147_483_647


def chamar(service, **params):
    raw = {
        "credential": "atendimento", "account_id": 17,
        "inbox_id": 4, "conversation_id": 482,
        **params,
    }
    return json.loads(service.execute("chatwoot_list_messages", raw))


def service_for(plugin, cfg, client):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    return ToolService(lambda: cfg, secret_provider=lambda key: (
        "https://chatwoot.exemplo.com" if key == "CHATWOOT_BASE_URL" else "token-teste"
    ), client_factory=lambda *_: client)


class Finder419(FakeClient):
    """Implementa os predicados e limites de MessageFinder no Chatwoot 4.19.0."""
    def __init__(self, items=None):
        super().__init__()
        if items is None:
            items = [
                # IDs 149/150 possuem created_at anterior ao que o ID sugere.
                {"id": mid, "created_at": 140 if mid == 149 else
                 141 if mid == 150 else mid}
                for mid in IDS
            ]
        self.items = items

    def list_messages(self, aid, cid, **kw):
        self.calls.append(("messages.list", aid, cid, kw))
        before, after = kw.get("before"), kw.get("after")
        if before is not None and after is not None:
            # messages_between: >= after e < before; before > INT_MAX
            # remove o limite superior. ORDER BY created_at ASC LIMIT 1000.
            filtered = [
                item for item in self.items
                if item["id"] >= after and
                (before > ID_MAX or item["id"] < before)
            ]
            payload = sorted(filtered, key=lambda m: m["created_at"])[:1000]
        elif before is not None:
            # messages_before: id < before, ORDER BY created_at DESC LIMIT 20
            selected = [m for m in self.items if m["id"] < before]
            payload = sorted(selected, key=lambda m: m["created_at"], reverse=True)[:20][::-1]
        elif after is not None:
            selected = [m for m in self.items if m["id"] > after]
            payload = sorted(selected, key=lambda m: m["created_at"])[:100]
        else:
            payload = sorted(self.items, key=lambda m: m["created_at"], reverse=True)[:20][::-1]
        return {"meta": {"labels": []}, "payload": payload}


def test_exemplo_real_perde_149_150_com_cursor_minimo(plugin, cfg):
    c = Finder419()
    first = c.list_messages(17, 482)["payload"]
    older = c.list_messages(17, 482, before=min(m["id"] for m in first))["payload"]
    ids = {m["id"] for m in first + older}
    assert len(first) == 20
    assert 149 not in ids and 150 not in ids
    assert len(ids) == 29  # regressao do algoritmo antigo


def test_summary_31_ids_unicos_e_primeira_mensagem(plugin, cfg):
    c = Finder419()
    result = chamar(service_for(plugin, cfg, c), summary=True)
    assert result["success"], result
    data = result["data"]
    assert data["complete"] is True
    assert data["unique_count"] == 31
    assert data["duplicate_count"] == 0
    assert data["pages_read"] == 1
    assert data["message_ids"] == IDS
    assert 149 in data["message_ids"] and 150 in data["message_ids"]
    assert data["first_message_id"] == 127
    assert data["last_message_id"] == 168
    assert data["first_chronological_id"] == 127
    assert data["chronology_verified"] is True
    assert c.calls[-1][-1] == {"after": 0, "before": ID_MAX + 1}


def test_summary_subdivide_limite_de_1000_sem_perder_ids(plugin, cfg):
    c = Finder419(items=[{"id": n, "created_at": 100000 + n} for n in range(1, 1006)])
    result = chamar(service_for(plugin, cfg, c), summary=True)
    assert result["success"], result
    assert result["data"]["unique_count"] == 1005
    assert result["data"]["message_ids"] == list(range(1, 1006))
    assert result["data"]["pages_read"] == 3
    assert all(
        "before" in call[3] and "after" in call[3]
        for call in c.calls if call[0] == "messages.list"
    )


def test_primeira_cronologica_nao_e_necessariamente_menor_id(plugin, cfg):
    items = [{"id": n, "created_at": 500 + n} for n in IDS]
    next(m for m in items if m["id"] == 160)["created_at"] = 1
    c = Finder419(items=items)
    result = chamar(service_for(plugin, cfg, c), summary=True)
    assert result["success"]
    assert result["data"]["first_message_id"] == 127
    assert result["data"]["first_chronological_id"] == 160


def test_modo_pagina_preserva_envelope_nativo(plugin, cfg):
    c = Finder419()
    result = chamar(service_for(plugin, cfg, c), before=160)
    assert result["success"]
    assert result["data"]["meta"] == {"labels": []}
    assert len(result["data"]["payload"]) == 20
    assert c.calls[-1][-1] == {"before": 160}


def test_summary_rejeita_cursor_e_tipo_invalido_sem_http(svc, factory):
    for value in (
        {"summary": True, "before": 200},
        {"summary": True, "after": 200},
        {"summary": "true"},
    ):
        assert chamar(svc, **value)["error"]["code"] == "invalid_arguments"
    assert not factory.clients


def test_api_ignora_intervalo_falha_fechado(plugin, cfg):
    class ApiComErro(FakeClient):
        def list_messages(self, aid, cid, **kw):
            return {"payload": [{"id": ID_MAX + 2}]}

    result = chamar(service_for(plugin, cfg, ApiComErro()), summary=True)
    assert result["error"]["code"] == "pagination_incomplete"
    assert "data" not in result


def test_summary_falha_fechado_com_payload_sem_id(plugin, cfg):
    class Invalid(FakeClient):
        def list_messages(self, aid, cid, **kw):
            return {"payload": [{"id": True}]}

    result = chamar(service_for(plugin, cfg, Invalid()), summary=True)
    assert result["error"]["code"] == "pagination_incomplete"


def test_limite_consultas_rejeita_total_parcial(plugin, cfg, monkeypatch):
    from hermes_chatwoot_v02_tests.chatwoot_tools.operations import messages
    monkeypatch.setattr(messages, "_MAX_QUERIES", 1)
    c = Finder419(items=[{"id": n, "created_at": n} for n in range(1, 1002)])
    result = chamar(service_for(plugin, cfg, c), summary=True)
    assert result["error"]["code"] == "pagination_incomplete"
    assert "data" not in result


def test_summary_conversa_vazia(plugin, cfg):
    c = Finder419(items=[])
    result = chamar(service_for(plugin, cfg, c), summary=True)
    assert result["success"] and result["data"]["complete"] is True
    assert result["data"]["unique_count"] == 0
    assert result["data"]["first_message_id"] is None
    assert result["data"]["first_chronological_id"] is None
