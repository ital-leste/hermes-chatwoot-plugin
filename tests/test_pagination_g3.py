"""G3: contagem deterministica com paginas sobrepostas, sem usar o LLM."""
import json

from conftest import FakeClient


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


class HistoricoSobreposto(FakeClient):
    ids = sorted([
        *range(127, 132), *range(142, 149),
        *range(151, 154), *range(155, 169),
    ])

    def __init__(self):
        super().__init__()
        self.pages = [
            [{"id": n} for n in reversed(self.ids[-20:])],
            [{"id": n} for n in reversed(self.ids[:9] + self.ids[-20:-18])],
            [],
        ]

    def list_messages(self, aid, cid, **kw):
        self.calls.append(("messages.list", aid, cid, kw))
        return {"meta": {"page_size": 20}, "payload": self.pages.pop(0)}


def test_historico_completo_29_ids_unicos_e_primeira(plugin, cfg):
    client = HistoricoSobreposto()
    result = chamar(service_for(plugin, cfg, client), summary=True)
    assert result["success"]
    data = result["data"]
    assert data["complete"] is True
    assert data["unique_count"] == 29
    assert data["duplicate_count"] == 2
    assert data["pages_read"] == 3
    assert data["first_message_id"] == 127
    assert data["last_message_id"] == 168
    assert data["message_ids"] == HistoricoSobreposto.ids
    assert [c[3] for c in client.calls if c[0] == "messages.list"] == [
        {}, {"before": 151}, {"before": 127},
    ]


def test_modo_pagina_preserva_envelope_nativo(plugin, cfg):
    client = HistoricoSobreposto()
    result = chamar(service_for(plugin, cfg, client), before=160)
    assert result["success"]
    assert result["data"]["meta"] == {"page_size": 20}
    assert len(result["data"]["payload"]) == 20
    assert client.calls[-1][-1] == {"before": 160}


def test_summary_rejeita_cursor_e_tipo_invalido_sem_http(svc, factory):
    for value in (
        {"summary": True, "before": 200},
        {"summary": True, "after": 200},
        {"summary": "true"},
    ):
        assert chamar(svc, **value)["error"]["code"] == "invalid_arguments"
    assert not factory.clients


def test_summary_falha_fechado_sem_progresso(plugin, cfg):
    class Loop(FakeClient):
        def list_messages(self, aid, cid, **kw):
            return {"payload": [{"id": 10}]}

    result = chamar(service_for(plugin, cfg, Loop()), summary=True)
    assert result["error"]["code"] == "pagination_incomplete"
    assert "data" not in result


def test_summary_falha_fechado_com_payload_sem_id(plugin, cfg):
    class Invalid(FakeClient):
        def list_messages(self, aid, cid, **kw):
            return {"payload": [{"id": True}]}

    result = chamar(service_for(plugin, cfg, Invalid()), summary=True)
    assert result["error"]["code"] == "pagination_incomplete"


def test_summary_conversa_vazia(plugin, cfg):
    class Empty(FakeClient):
        def list_messages(self, aid, cid, **kw):
            return {"payload": []}

    result = chamar(service_for(plugin, cfg, Empty()), summary=True)
    assert result["success"] and result["data"]["complete"] is True
    assert result["data"]["unique_count"] == 0
    assert result["data"]["first_message_id"] is None
