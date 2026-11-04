from __future__ import annotations
import json
import copy
import pytest
from conftest import FakeClient


def run(svc,name="chatwoot_get_conversation", **values):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import _CONVERSATION,_CONTACT
    kwargs={"account_id":17,"inbox_id":4}
    if name in _CONVERSATION: kwargs["conversation_id"]=482
    if name in _CONTACT: kwargs["contact_id"]=25
    kwargs.update(values)
    return json.loads(svc.execute(name, kwargs))


def test_leitura_triangulada_e_payload_integral(svc, factory):
    v=run(svc)
    assert v["success"] and v["data"]["sensitive"]["raw"]=="kept"
    assert factory.clients[0].calls==[("conversation.get",17,482)]
    assert factory.clients[0].closed
    assert factory.urls==[("https://chatwoot.exemplo.com","token_value")]


def test_publicacao_e_guardia_previa(svc,factory):
    v=run(svc,"chatwoot_send_public_message",content="Bom dia")
    assert v["success"] and v["data"]["sender"]["phone"]=="+5511999"
    assert factory.clients[0].calls==[("conversation.get",17,482),("messages.send_text",17,482,"Bom dia",False)]


def test_inbox_errada_bloqueia_escrita(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    c=FakeClient(inbox=6)
    svc=ToolService(lambda:cfg,secret_provider=lambda _:"x",client_factory=lambda *a:c)
    r=run(svc,"chatwoot_send_public_message",content="x")
    assert r["error"]["code"]=="scope_denied"
    assert c.calls==[("conversation.get",17,482)]


def test_conversation_errada_bloqueia_escrita(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    c=FakeClient(cid=483)
    svc=ToolService(lambda:cfg,secret_provider=lambda _:"x",client_factory=lambda *a:c)
    r=run(svc,"chatwoot_set_status",status="open")
    assert r["error"]["code"]=="scope_denied"
    assert c.calls==[("conversation.get",17,482)]


def test_nota_privada_desautorizada_sem_http(svc, factory):
    r=run(svc,"chatwoot_send_private_note",content="interno")
    assert r["error"]["code"]=="operation_denied"
    assert not factory.clients


def test_nota_privada_autorizada(svc,cfg,factory):
    cfg["allowed_operations"]["messages.send_private"]=True
    assert run(svc,"chatwoot_send_private_note",content="interno")["success"]
    assert factory.clients[0].calls[-1][-1] is True


def test_lista_conversa_filtra_inbox_e_preserva_envelope(svc,factory):
    r=run(svc,"chatwoot_list_conversations",status="open",page=1)
    assert r["success"] and r["data"]["data"]["meta"]=={"total":1}
    assert factory.clients[0].calls==[("conversations.list",17,{"inbox_id":4,"status":"open","page":1})]


def test_lista_inbox_errada_rejeita(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    c=FakeClient(conversations=[{"id":12,"inbox_id":8}])
    svc=ToolService(lambda:cfg,secret_provider=lambda _:"x",client_factory=lambda *a:c)
    assert run(svc,"chatwoot_list_conversations")["error"]["code"]=="scope_denied"


def test_lesse_mensagens(svc,factory):
    r=run(svc,"chatwoot_list_messages",before=0)
    assert r["success"] and r["data"]["payload"][0]["content"]=="mensagem integral"
    assert factory.clients[0].calls[-1]==("messages.list",17,482,{"before":0})


def test_status_etiquetas(svc,factory):
    assert run(svc,"chatwoot_set_status",status="snoozed",snoozed_until=1790000000)["success"]
    assert run(svc,"chatwoot_add_labels",labels=["g"])["success"]
    assert run(svc,"chatwoot_remove_labels",labels=["g"])["success"]
    assert factory.clients[0].calls[-1][-1]=={"snoozed_until":1790000000}


def test_contato_associado(svc,factory):
    r=run(svc,"chatwoot_get_contact")
    assert r["success"] and r["data"]["contact_inboxes"][0]["inbox"]["id"]==4


def test_conversas_contato_filtradas_por_inbox(svc):
    r=run(svc,"chatwoot_get_contact_conversations")
    assert r["success"] and [x["id"] for x in r["data"]["payload"]]==[482]


def test_contato_sem_associacao_bloqueado(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    class NoAssociation(FakeClient):
        def contact_conversations(self,a,id):
            return {"payload":[]}
    c=NoAssociation(contact_inboxes=(8,))
    c.contacts.list_conversations=c.contact_conversations
    svc=ToolService(lambda:cfg,secret_provider=lambda _:"x",client_factory=lambda *a:c)
    assert run(svc,"chatwoot_update_contact",fields={"name":"Novo"})["error"]["code"]=="scope_denied"
    assert not any(x[0]=="contacts.update" for x in c.calls)


def test_busca_contato_restringe_inbox(svc,factory):
    r=run(svc,"chatwoot_search_contacts",q="Cliente")
    assert r["success"] and r["data"]["payload"][0]["id"]==25
    assert factory.clients[0].calls[-1][0]=="contacts.get"


def test_busca_contato_nao_vinculado(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    c=FakeClient(contact_inboxes=(8,))
    svc=ToolService(lambda:cfg,secret_provider=lambda _:"x",client_factory=lambda *a:c)
    # contato 25 possui conversa histórica na inbox 4, comprovada pela API
    assert run(svc,"chatwoot_search_contacts",q="Cliente")["success"]
    assert any(x[0]=="contacts.list_conversations" for x in c.calls)


def test_atualizacao_campos_permitidos(svc,factory):
    r=run(svc,"chatwoot_update_contact",fields={"name":"Maria","phone_number":"+5511999999999"})
    assert r["success"] and r["data"]["updated"]["name"]=="Maria"
    assert factory.clients[0].calls[-1][0]=="contacts.update"


def test_atualizacao_email_proibido(svc,factory):
    r=run(svc,"chatwoot_update_contact",fields={"name":"Maria","email":"maria@example.org"})
    assert r["error"]["code"]=="operation_denied" and not factory.clients


@pytest.mark.parametrize("name,kwargs", [
    ("chatwoot_send_public_message",{"content":" "}),
    ("chatwoot_send_public_message",{"token":"secret","content":"Oi"}),
    ("chatwoot_get_conversation",{"inbox_id":True}),
    ("chatwoot_get_conversation",{"conversation_id":0}),
    ("chatwoot_list_conversations",{"page":0}),
    ("chatwoot_list_conversations",{"status":"banana"}),
    ("chatwoot_set_status",{"status":"open","snoozed_until":100}),
    ("chatwoot_add_labels",{"labels":[]}),
    ("chatwoot_search_contacts",{"q":" "}),
    ("chatwoot_update_contact",{"fields":{"unexpected":123}}),
])
def test_argumentos_invalidos(svc,factory,name,kwargs):
    assert run(svc,name,**kwargs)["error"]["code"]=="invalid_arguments"
    assert not factory.clients


def test_credenciais_ausentes(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    svc=ToolService(lambda:cfg,secret_provider=lambda _:None)
    assert run(svc)["error"]["code"]=="credentials_unavailable"


def test_timeout_em_guardia_nao_resultado_indeterminado(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    c=FakeClient(fail=TimeoutError("sensitive secret"))
    svc=ToolService(lambda:cfg,secret_provider=lambda _:"x",client_factory=lambda *a:c)
    assert run(svc,"chatwoot_send_public_message",content="Oi")["error"]["code"]=="execution_error"


def test_timeout_depois_da_guardia_indeterminado(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    class TimeoutOnWrite(FakeClient):
        def send_text(self,a,c,message):
            raise TimeoutError("secret 123")
    c=TimeoutOnWrite()
    c.messages.send_text=c.send_text
    svc=ToolService(lambda:cfg,secret_provider=lambda _:"x",client_factory=lambda *a:c)
    r=run(svc,"chatwoot_send_public_message",content="Oi")
    assert r["error"]["code"]=="outcome_unknown"
    assert "secret" not in json.dumps(r)
