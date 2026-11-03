from __future__ import annotations

import copy
import json
import pytest


def call(service, name="chatwoot_get_conversation", **kw):
    data = {"installation":"principal", "account_id":17, "conversation_id":42}
    data.update(kw)
    return json.loads(service.execute(name, data))


def test_consulta_validada(service, factory):
    response = call(service)
    assert response["success"] is True
    assert response["data"]["inbox_id"] == 4
    assert factory.clients[0][2].closed


def test_bloqueia_operacao_sem_cliente(service, factory):
    response = call(service, "chatwoot_send_private_note", content="nota")
    assert response["error"]["code"] == "operation_denied"
    assert not factory.clients


def test_bloqueia_conta(service, factory):
    response = call(service, account_id=12)
    assert response["error"]["code"] == "scope_denied"
    assert not factory.clients


def test_instalacao_inexistente(service, factory):
    response = call(service, installation="outra")
    assert response["error"]["code"] == "operation_denied"
    assert not factory.clients


def test_publica_com_trava_de_inbox(service, factory):
    response = call(service, "chatwoot_send_public_message", content="Olá")
    assert response["success"] is True
    assert factory.clients[0][2].calls == [
        ("get",17,42), ("send_text",17,42,"Olá",False)
    ]


def test_escopo_inbox_divergente_sem_escrita(plugin, configured, fake_chatwoot):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.service import ToolService
    from conftest import FakeClient
    clients = []
    def factory(url, tok):
        c = FakeClient(inbox_id=9); clients.append(c); return c
    svc = ToolService(lambda: configured, secret_provider=lambda k:"token", client_factory=factory)
    response = call(svc, "chatwoot_send_public_message", content="Não enviar")
    assert response["error"]["code"] == "scope_denied"
    assert clients[0].calls == [("get",17,42)]


def test_escopo_resposta_com_id_divergente(plugin, configured, fake_chatwoot):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.service import ToolService
    from conftest import FakeClient
    client=FakeClient(conversation_id=100)
    svc=ToolService(lambda: configured, secret_provider=lambda _:"token", client_factory=lambda a,b:client)
    response=call(svc,"chatwoot_send_public_message",content="não")
    assert response["error"]["code"] == "scope_denied"
    assert len(client.calls) == 1


def test_nota_privada_quando_autorizada(service, configured, factory):
    configured["principal"]["allowed_operations"]["messages.send_private"] = True
    response=call(service, "chatwoot_send_private_note", content="privado")
    assert response["success"]
    assert factory.clients[0][2].calls[-1][-1] is True


def test_leitura_com_cursor_zero(service, factory):
    response=call(service, "chatwoot_list_messages", before=0)
    assert response["success"]
    assert factory.clients[0][2].calls[-1] == ("list",17,42,{"before":0})


def test_status_tipado(service, factory):
    result=call(service,"chatwoot_set_status", status="snoozed",snoozed_until=1790000000)
    assert result["success"]
    assert factory.clients[0][2].calls[-1][0] == "set_status"
    assert factory.clients[0][2].calls[-1][-1] == {"snoozed_until":1790000000}


@pytest.mark.parametrize("tool,kwargs", [
    ("chatwoot_send_public_message",{"content":"  "}),
    ("chatwoot_send_public_message",{"content":"X", "token":"secret"}),
    ("chatwoot_set_status",{"status":"unknown"}),
    ("chatwoot_set_status",{"status":"open","snoozed_until":179}),
    ("chatwoot_list_messages",{"before":-1}),
    ("chatwoot_add_labels",{"labels":["ok",123]}),
    ("chatwoot_remove_labels",{"labels":[]}),
    ("chatwoot_get_conversation",{"account_id":True}),
    ("chatwoot_get_conversation",{"conversation_id":0}),
])
def test_argumentos_invalidos_sem_cliente(service,factory,tool,kwargs):
    resp=call(service,tool,**kwargs)
    assert resp["error"]["code"] == "invalid_arguments"
    assert not factory.clients


@pytest.mark.parametrize("name", ["chatwoot_add_labels", "chatwoot_remove_labels"])
def test_operacoes_etiquetas(service,factory,name):
    response=call(service,name,labels=["priority"])
    assert response["success"]
    assert factory.clients[0][2].calls[-1][0] in {"add","remove"}


def test_segunda_instalacao_sem_trava_inbox(plugin, configured, fake_chatwoot):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.service import ToolService
    from conftest import FakeClient
    instance=FakeClient()
    clients=[]
    def make(url, token):
        clients.append((url,token));return instance
    svc=ToolService(lambda: configured, secret_provider=lambda env:env+"-secret", client_factory=make)
    result=call(svc,"chatwoot_list_messages",installation="homolog",account_id=1)
    assert result["success"]
    assert clients == [("http://127.0.0.1:3000","CHATWOOT_HOMOLOG_TOKEN-secret")]
    assert instance.calls == [("list",1,42,{})]


def test_falha_credencial_nunca_tenta_http(plugin,configured,fake_chatwoot):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.service import ToolService
    svc=ToolService(lambda: configured, secret_provider=lambda _:None)
    result=call(svc)
    assert result["error"]["code"]=="credentials_unavailable"


def test_muda_config_entre_chamadas(service,configured,factory):
    assert call(service,"chatwoot_send_public_message",content="oi")["success"]
    configured["principal"]["allowed_operations"]["messages.send_public"] = False
    assert call(service,"chatwoot_send_public_message",content="oi")["error"]["code"]=="operation_denied"
    assert len(factory.clients)==1


def test_falha_http_nao_vaza_corpo(plugin,configured,fake_chatwoot):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.service import ToolService
    from conftest import FakeClient
    class ApiException(Exception):
        status_http = 403
    client=FakeClient(fail=ApiException("token:TOPSECRET payload:SECRET"))
    svc=ToolService(lambda:configured,secret_provider=lambda _:"secret",client_factory=lambda a,b:client)
    result=call(svc,"chatwoot_send_public_message",content="Oi")
    raw=json.dumps(result)
    assert result["error"]["code"] == "chatwoot_api_error"
    assert result["error"]["status_http"]==403
    assert "TOPSECRET" not in raw and "payload:SECRET" not in raw


def test_falha_indeterminada_em_escrita(plugin,configured,fake_chatwoot):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.service import ToolService
    from conftest import FakeClient
    client=FakeClient(fail=RuntimeError("network timeout contains secret"))
    svc=ToolService(lambda:configured,secret_provider=lambda _:"secret",client_factory=lambda a,b:client)
    result=call(svc,"chatwoot_send_public_message",content="oi")
    assert result["error"]["code"]=="outcome_unknown"
    assert "secret" not in json.dumps(result)
