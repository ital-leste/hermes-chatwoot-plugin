"""Regressões do plugin através do SDK REAL e httpx.MockTransport.

O SDK é instalado em versão Git fixa pelo workflow; estes testes não substituem
os testes unitários isolados e nunca realizam chamadas reais à rede.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import httpx
import jsonschema
import pytest

sdk = pytest.importorskip("chatwoot_client")

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def service_module(monkeypatch):
    name = "hermes_chatwoot_real_sdk_contracts"
    for item in list(sys.modules):
        if item == name or item.startswith(name + "."):
            monkeypatch.delitem(sys.modules, item, raising=False)
    spec = importlib.util.spec_from_file_location(name, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return __import__(f"{name}.chatwoot_tools.service", fromlist=["ToolService"])


@pytest.fixture
def setup(service_module):
    class Context:
        def __init__(self):
            self.calls = []
            self.callback = lambda request: httpx.Response(404, json={"error": "not_found"})
            self.settings = {
                "base_url_env": "CHATWOOT_BASE_URL",
                "credentials": {"atendimento": {"token_env": "CHATWOOT_TEST_TOKEN", "account_id": 17}},
                "allowed_operations": {name: True for name in service_module.TOOLS_TO_OPERATIONS.values()},
                "writable_contact_fields": {name: True for name in (
                    "name", "email", "phone_number", "identifier", "blocked", "avatar_url", "custom_attributes", "additional_attributes"
                )},
            }

        def factory(self, url, token):
            assert url == "https://chatwoot.exemplo.com" and token == "token-ficticio"
            cw = sdk.CWClient(url, token)
            cw._http.close()

            def handle(req):
                self.calls.append((req.method, req.url.path))
                return self.callback(req)

            cw._http = httpx.Client(base_url=url + "/", transport=httpx.MockTransport(handle))
            return cw

        def service(self, client_factory=None):
            return service_module.ToolService(
                lambda: self.settings,
                secret_provider=lambda key: {
                    "CHATWOOT_BASE_URL": "https://chatwoot.exemplo.com",
                    "CHATWOOT_TEST_TOKEN": "token-ficticio",
                }.get(key), client_factory=client_factory or self.factory,
            )

        def call(self, tool, **kwargs):
            data = {"credential": "atendimento", "account_id": 17, "inbox_id": 4}
            if tool in service_module._CONVERSATION:
                data["conversation_id"] = 482
            if tool in service_module._CONTACT:
                data["contact_id"] = 25
            data.update(kwargs)
            return json.loads(self.service().execute(tool, data))

    return Context()


CONV = "/api/v1/accounts/17/conversations/482"
CONTACT = "/api/v1/accounts/17/contacts/25"
CONTACT_HISTORY = CONTACT + "/conversations"
CONTACT_SEARCH = "/api/v1/accounts/17/contacts/search"
MSG = CONV + "/messages"
LABELS = CONV + "/labels"


def conversation_response(req):
    return httpx.Response(200, json={"id": 482, "inbox_id": 4, "account_id": 17})


def contact_envelope(form="payload", *, cid=25, aid=17, inbox=4, history=False):
    obj = {"id": cid, "account_id": aid, "name": "Cliente", "custom_attributes": {"grupo": {"a": 1}}}
    if not history:
        obj["contact_inboxes"] = [{"inbox": {"id": inbox}}]
    if form == "flat":
        return obj
    if form == "data.payload":
        return {"data": {"payload": obj}}
    if form == "payload.contact":
        return {"payload": {"contact": obj}}
    return {"payload": obj}


@pytest.mark.parametrize("form", ["flat", "payload", "payload.contact", "data.payload"])
def test_get_contact_devolve_envelope_original_e_preserva_campos(setup, form):
    expected = contact_envelope(form)
    setup.callback = lambda req: httpx.Response(200, json=expected)
    got = setup.call("chatwoot_get_contact")
    assert got["success"] and got["data"] == expected
    assert setup.calls == [("GET", CONTACT)]


@pytest.mark.parametrize("bad", [
    {"id": 25, "payload": {"id": 25}},
    {"payload": {"id": 25, "contact": {"id": 25}}},
    {"payload": {"id": True}}, {"payload": {"id": None}},
    {"payload": {"id": "25"}}, {"payload": {"id": -1}},
    contact_envelope(cid=26), contact_envelope(aid=18),
])
def test_contato_invalido_ou_ambiguo_falha_fechado(setup, bad):
    setup.callback = lambda req: httpx.Response(200, json=bad)
    got = setup.call("chatwoot_get_contact")
    assert got["error"]["code"] == "scope_denied"
    assert setup.calls == [("GET", CONTACT)]


def test_historico_de_contato_em_envelope_e_filtragem_por_inbox(setup):
    original = {"payload": [{"id": 31, "inbox_id": 4, "account_id": 17, "other": {"x": 1}},
                            {"id": 32, "inbox_id": 8, "account_id": 17}], "meta": {"total": 2}}
    def handler(req):
        if req.url.path == CONTACT:
            return httpx.Response(200, json=contact_envelope())
        return httpx.Response(200, json=original)
    setup.callback = handler
    got = setup.call("chatwoot_get_contact_conversations")
    assert got["success"]
    assert got["data"] == {"payload": [original["payload"][0]], "meta": {"total": 2}}
    assert original["payload"][1]["id"] == 32
    assert setup.calls == [("GET", CONTACT), ("GET", CONTACT_HISTORY)]


@pytest.mark.parametrize("bad", [
    {"id": 33, "inbox_id": 4, "account_id": 18},
    {"id": 33, "inbox_id": 4, "contact_id": 99},
    {"id": 33, "inbox_id": 4, "account_id": True},
])
def test_historico_contaditorio_rejeitado(setup, bad):
    def handler(req):
        if req.url.path == CONTACT:
            return httpx.Response(200, json=contact_envelope())
        return httpx.Response(200, json={"payload": [bad]})
    setup.callback = handler
    assert setup.call("chatwoot_get_contact_conversations")["error"]["code"] == "scope_denied"


def test_busca_reconhece_associacao_no_detalhe_com_historico_vazio(setup):
    def handler(req):
        if req.url.path == CONTACT_SEARCH:
            return httpx.Response(200, json={"payload": [{"id": 25, "name": "Cliente"}], "meta": {"total": 1}})
        if req.url.path == CONTACT:
            return httpx.Response(200, json=contact_envelope())
        raise AssertionError("Historico nao deve ser consultado apos vinculo comprovado")
    setup.callback = handler
    out = setup.call("chatwoot_search_contacts", q="Cliente")
    assert out["success"] and out["data"]["payload"] == [{"id": 25, "name": "Cliente"}]
    assert setup.calls == [("GET", CONTACT_SEARCH), ("GET", CONTACT)]


@pytest.mark.parametrize("candidate,detail", [
    ({"id": 25, "name": "Cliente"}, contact_envelope(cid=26)),
    ({"id": 25, "name": "Cliente", "account_id": 18, "contact_inboxes": [{"inbox_id": 4}]}, None),
])
def test_busca_nao_aceita_identidade_divergente(setup, candidate, detail):
    def handler(req):
        if req.url.path == CONTACT_SEARCH:
            return httpx.Response(200, json={"payload": [candidate]})
        if req.url.path == CONTACT:
            return httpx.Response(200, json=detail)
        raise AssertionError("Nao chamar historico depois de contradicao")
    setup.callback = handler
    assert setup.call("chatwoot_search_contacts", q="Cliente")["error"]["code"] == "scope_denied"
    assert not any(path == CONTACT_HISTORY for _, path in setup.calls)


def test_busca_pagina_vazia_pode_preservar_meta_pre_filtro(setup):
    def handler(req):
        if req.url.path == CONTACT_SEARCH:
            return httpx.Response(200, json={"payload": [{"id": 25}], "meta": {"total": 250, "page": 1}})
        if req.url.path == CONTACT:
            return httpx.Response(200, json=contact_envelope(inbox=8, history=False))
        return httpx.Response(200, json={"payload": []})
    setup.callback = handler
    out = setup.call("chatwoot_search_contacts", q="Cliente", page=1)
    assert out["success"] and out["data"]["payload"] == []
    assert out["data"]["meta"] == {"total": 250, "page": 1}
    assert setup.calls == [("GET", CONTACT_SEARCH), ("GET", CONTACT), ("GET", CONTACT_HISTORY)]


def test_get_contact_permite_conversa_historica_com_associacao_compativel(setup):
    def handler(req):
        if req.url.path == CONTACT:
            return httpx.Response(200, json=contact_envelope(history=True))
        return httpx.Response(200, json={"payload": [{"id": 3, "inbox_id": 4, "account_id": 17, "contact_id": 25}]})
    setup.callback = handler
    out = setup.call("chatwoot_get_contact")
    assert out["success"]
    assert setup.calls == [("GET", CONTACT), ("GET", CONTACT_HISTORY)]


def test_historico_nao_aceita_conta_contraditoria_em_fallback(setup):
    def handler(req):
        if req.url.path == CONTACT:
            return httpx.Response(200, json=contact_envelope(history=True))
        return httpx.Response(200, json={"payload": [{"id": 31, "inbox_id": 4, "account_id": 18}]})
    setup.callback = handler
    assert setup.call("chatwoot_get_contact")["error"]["code"] == "scope_denied"


@pytest.mark.parametrize("status, body, expected", [
    (201, b"not-json", "outcome_unknown"),
    (200, b"not-json", "outcome_unknown"),
    (500, b'{"message":"failure"}', "outcome_unknown"),
    (401, b'{"message":"unauthorized"}', "chatwoot_api_error"),
    (422, b'{"message":"invalid"}', "chatwoot_api_error"),
])
def test_publicacao_classifica_resultados_do_sdk_real(setup, status, body, expected):
    def handler(req):
        if req.url.path == CONV:
            return conversation_response(req)
        assert req.url.path == MSG and req.method == "POST"
        return httpx.Response(status, content=body)
    setup.callback = handler
    out = setup.call("chatwoot_send_public_message", content="Oi")
    assert out["error"]["code"] == expected
    assert setup.calls == [("GET", CONV), ("POST", MSG)]


def test_publicacao_retorna_json_do_sdk_integral(setup):
    expected = {"id": 9, "created_at": 1793790000, "sender": {"id": 6}, "content_attributes": {"x": 1}}
    setup.callback = lambda req: conversation_response(req) if req.url.path == CONV else httpx.Response(201, json=expected)
    out = setup.call("chatwoot_send_public_message", content="Oi")
    assert out["success"] and out["data"] == expected
    assert setup.calls == [("GET", CONV), ("POST", MSG)]


def test_timeout_de_publicacao_nao_reenvia(setup):
    def handler(req):
        if req.url.path == CONV:
            return conversation_response(req)
        raise httpx.ReadTimeout("timeout sintético", request=req)
    setup.callback = handler
    out = setup.call("chatwoot_send_public_message", content="Oi")
    assert out["error"]["code"] == "outcome_unknown"
    assert setup.calls == [("GET", CONV), ("POST", MSG)]
    assert "timeout" not in json.dumps(out).lower()


def test_erro_em_guardia_nunca_marca_escrita(setup):
    setup.callback = lambda req: httpx.Response(500, json={"error": "db down"})
    out = setup.call("chatwoot_send_public_message", content="Oi")
    assert out["error"]["code"] == "chatwoot_api_error"
    assert setup.calls == [("GET", CONV)]


def test_erro_serializacao_apos_escrita_incerto(setup):
    def handler(req):
        if req.url.path == CONV:
            return conversation_response(req)
        return httpx.Response(201, content=b'{"id":33,"value":NaN}')
    setup.callback = handler
    out = setup.call("chatwoot_send_public_message", content="Oi")
    assert out["error"]["code"] == "outcome_unknown"
    assert setup.calls == [("GET", CONV), ("POST", MSG)]


def test_falha_na_finalizacao_do_cliente_apos_escrita(setup):
    class FailsOnExit:
        def __init__(self, client):
            self.client = client
        def __enter__(self):
            return self.client.__enter__()
        def __exit__(self, *args):
            self.client.__exit__(*args)
            raise ValueError("segredo-ficticio")
    setup.callback = lambda req: conversation_response(req) if req.url.path == CONV else httpx.Response(201, json={"id": 90})
    out = json.loads(setup.service(client_factory=lambda url, token: FailsOnExit(setup.factory(url,token))).execute(
        "chatwoot_send_public_message", {"credential":"atendimento", "account_id":17, "inbox_id":4,
        "conversation_id":482, "content":"Oi"}))
    # O transporte simulado não confirma resultado, mas a falha de saída não
    # pode ser classificada como argumentos inválidos.
    assert out["error"]["code"] == "outcome_unknown"
    assert setup.calls == [("GET", CONV), ("POST", MSG)]
    assert "segredo-ficticio" not in json.dumps(out)


def test_etiquetas_sem_mudanca_somente_get(setup):
    def handler(req):
        if req.url.path == CONV:
            return conversation_response(req)
        assert req.url.path == LABELS and req.method == "GET"
        return httpx.Response(200, json={"payload": ["existente"]})
    setup.callback = handler
    out = setup.call("chatwoot_add_labels", labels=["existente"])
    assert out["success"]
    assert setup.calls == [("GET", CONV), ("GET", LABELS)]


def test_etiquetas_get_interno_falha_sem_post(setup):
    def handler(req):
        if req.url.path == CONV:
            return conversation_response(req)
        assert req.method == "GET"
        return httpx.Response(500, json={"error": "read failed"})
    setup.callback = handler
    out = setup.call("chatwoot_add_labels", labels=["nova"])
    assert out["error"]["code"] == "outcome_unknown"  # GET interno não é observável pelo plugin.
    assert setup.calls == [("GET", CONV), ("GET", LABELS)]


def test_etiquetas_mudanca_get_e_post(setup):
    def handler(req):
        if req.url.path == CONV:
            return conversation_response(req)
        if req.method == "GET":
            return httpx.Response(200, json={"payload": ["antiga"]})
        return httpx.Response(200, json={"payload": ["antiga", "nova"]})
    setup.callback = handler
    out = setup.call("chatwoot_add_labels", labels=["nova"])
    assert out["success"]
    assert setup.calls == [("GET", CONV), ("GET", LABELS), ("POST", LABELS)]


@pytest.mark.parametrize("fields,success", [
    ({"name": None}, True), ({"blocked": False}, True),
    ({"custom_attributes": {}}, True),
    ({"additional_attributes": {"aninhado": {"livre": [1, 2, True, None]}}}, True),
    ({"blocked": "false"}, False), ({"blocked": None}, False),
    ({"phone_number": "1199999"}, False),
    ({"custom_attributes": {"invalido": math.nan}}, False),
    ({"additional_attributes": {"invalido": math.inf}}, False),
])
def test_schema_campos_e_sdk_contact(fields, success):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("schema_rc4_real", ROOT / "schemas.py")
    schema_module = module_from_spec(spec)
    spec.loader.exec_module(schema_module)
    s = schema_module.CONTACT_FIELDS
    jsonschema.Draft7Validator.check_schema(s)
    valid_schema = not list(jsonschema.Draft7Validator(s).iter_errors(fields))
    if not success:
        if valid_schema and any(isinstance(v, float) and not math.isfinite(v) for item in fields.values() for v in (item.values() if isinstance(item, dict) else [item])):
            # JSON Schema admite numbers; finitude é garantida pelo contrato Python.
            pass
        else:
            assert not valid_schema
        with pytest.raises((ValueError, TypeError)):
            sdk.Contact(**fields)
    else:
        assert valid_schema
        assert sdk.Contact(**fields).to_payload() == fields


def test_atualizacao_contato_campos_tipados_antes_da_rede(setup):
    out = setup.call("chatwoot_update_contact", fields={"blocked":"false"})
    assert out["error"]["code"] == "invalid_arguments" and not setup.calls


def test_atualizacao_contato_envelope_e_json_original(setup):
    def handler(req):
        if req.url.path == CONTACT:
            if req.method == "GET":
                return httpx.Response(200, json=contact_envelope())
            assert req.method == "PUT"
            return httpx.Response(200, json={"payload": {"id":25,"name":None,"blocked":False},"meta":{"source":"api"}})
        raise AssertionError(f"Rota nao esperada: {req.url.path}")
    setup.callback = handler
    out = setup.call("chatwoot_update_contact", fields={"name": None, "blocked":False})
    assert out["success"] and out["data"]["payload"]["blocked"] is False
    assert out["data"]["meta"] == {"source": "api"}
    assert setup.calls == [("GET", CONTACT), ("PUT", CONTACT)]
@pytest.mark.parametrize("fields", [
    {"email": "a@b\n"},
    {"phone_number": "+55123\n"},
])
def test_schema_rejeita_quebra_linha_final_antes_de_acessar_api(setup, fields):
    """JSON Schema, SDK Contact e serviço devem rejeitar o mesmo valor sem HTTP."""
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("schema_rc4_end_of_string", ROOT / "schemas.py")
    schema_module = module_from_spec(spec)
    spec.loader.exec_module(schema_module)
    validator = jsonschema.Draft7Validator(schema_module.CONTACT_FIELDS)
    assert list(validator.iter_errors(fields)), "Schema não pode anunciar contrato mais amplo que SDK"
    with pytest.raises((ValueError, TypeError)):
        sdk.Contact(**fields)
    result = setup.call("chatwoot_update_contact", fields=fields)
    assert result["error"]["code"] == "invalid_arguments"
    assert setup.calls == []


@pytest.mark.parametrize("fields", [
    {"email": "a@b"},
    {"phone_number": "+55123"},
])
def test_schema_aceita_casos_validos_sem_mudar_valor(fields):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("schema_rc4_valid_end", ROOT / "schemas.py")
    schema_module = module_from_spec(spec)
    spec.loader.exec_module(schema_module)
    assert not list(jsonschema.Draft7Validator(schema_module.CONTACT_FIELDS).iter_errors(fields))
    assert sdk.Contact(**fields).to_payload() == fields


@pytest.mark.parametrize("media_status,code", [
    (302, "media_redirect_rejected"),
    (404, "media_unavailable"),
])
def test_sdk_real_classifica_download_antes_do_post(setup, monkeypatch, media_status, code):
    import socket
    from types import SimpleNamespace
    from chatwoot_client import attachment_resolver as resolver

    setup.settings["media_allowed_hosts"] = ["files.example.org"]
    setup.callback = lambda req: conversation_response(req)
    downloads = []
    original_client = httpx.Client

    def download_client(*args, **kwargs):
        assert kwargs["follow_redirects"] is False
        assert kwargs["trust_env"] is False
        return original_client(transport=httpx.MockTransport(
            lambda req: (downloads.append(req) or httpx.Response(
                media_status, headers={"location": "https://outro.example.org/f.pdf"}
            ))
        ))

    monkeypatch.setattr(resolver, "httpx", SimpleNamespace(
        Client=download_client, HTTPError=httpx.HTTPError,
    ))
    monkeypatch.setattr(resolver.socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
    ])
    result = setup.call(
        "chatwoot_send_media", media_url="https://files.example.org/a.pdf",
        mime_type="application/pdf", filename="a.pdf",
    )
    assert result["error"]["code"] == code
    assert setup.calls == [("GET", CONV)]
    assert len(downloads) == 1
    assert "Authorization" not in downloads[0].headers


def test_summary_sdk_real_intervalo_inclui_mensagens_fora_de_ordem(setup):
    """Exercita contrato HTTP real do SDK, sem writes nem JSON falso da ferramenta."""
    ids = sorted([*range(127, 132), *range(142, 154), *range(155, 169)])
    messages = [
        {"id": mid, "created_at": (140 if mid == 149 else 141 if mid == 150 else mid)}
        for mid in ids
    ]
    queries = []

    def handler(req):
        if req.url.path == CONV:
            return conversation_response(req)
        assert req.url.path == MSG and req.method == "GET"
        params = dict(req.url.params)
        queries.append(params)
        low, high = int(params["after"]), int(params["before"])
        payload = [
            row for row in messages
            if row["id"] >= low and (high > 2_147_483_647 or row["id"] < high)
        ]
        return httpx.Response(
            200, json={"meta": {}, "payload": sorted(
                payload, key=lambda m: m["created_at"]
            )[:1000]},
        )

    setup.callback = handler
    out = setup.call("chatwoot_list_messages", summary=True)
    assert out["success"], out
    assert out["data"]["unique_count"] == 31
    assert out["data"]["first_message_id"] == 127
    assert 149 in out["data"]["message_ids"]
    assert 150 in out["data"]["message_ids"]
    assert queries == [{"after": "0", "before": "2147483648"}]
    assert setup.calls == [("GET", CONV), ("GET", MSG)]
