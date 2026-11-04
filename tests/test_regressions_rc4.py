from __future__ import annotations
import json
import pytest
from conftest import FakeClient


def service(plugin, cfg, client):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    return ToolService(lambda: cfg, secret_provider=lambda name: (
        "https://chatwoot.exemplo.com" if name == "CHATWOOT_BASE_URL" else "token"
    ), client_factory=lambda *_: client)


def invoke(svc, name, **kwargs):
    values = {"credential": "atendimento", "account_id": 17, "inbox_id": 4}
    if name in ("chatwoot_get_contact", "chatwoot_get_contact_conversations", "chatwoot_update_contact"):
        values["contact_id"] = 25
    else:
        values["conversation_id"] = 482
    values.update(kwargs)
    return json.loads(svc.execute(name, values))


def test_contact_payload_preserved(plugin, cfg):
    class Wrapped(FakeClient):
        def get_contact(self, a, contact_id):
            value = super().get_contact(a, contact_id)
            return {"payload": {**value, "custom_attributes": {"nested": {"value": 1}}}, "meta": {"original": True}}
    c = Wrapped()
    result = invoke(service(plugin, cfg, c), "chatwoot_get_contact")
    assert result["success"]
    assert result["data"]["meta"] == {"original": True}
    assert result["data"]["payload"]["custom_attributes"]["nested"]["value"] == 1


@pytest.mark.parametrize("bad", [
    {"payload": {"id": True, "contact_inboxes": [{"inbox": {"id": 4}}]}},
    {"payload": {"id": 25}, "id": 25},
    {"payload": None},
    {"payload": {"id": 26, "contact_inboxes": [{"inbox": {"id": 4}}]}},
])
def test_contact_invalid_or_ambiguous(plugin, cfg, bad):
    class Wrapped(FakeClient):
        def get_contact(self, a, contact_id):
            self.calls.append(("contacts.get", a, contact_id))
            return bad
    c = Wrapped()
    result = invoke(service(plugin, cfg, c), "chatwoot_get_contact")
    assert result["error"]["code"] == "scope_denied"


def test_search_candidate_detail_mismatch(plugin, cfg):
    class Mismatch(FakeClient):
        def get_contact(self, a, contact_id):
            self.calls.append(("contacts.get", a, contact_id))
            return {"payload": {"id": 99, "contact_inboxes": [{"inbox": {"id": 4}}]}}
    c = Mismatch()
    result = json.loads(service(plugin, cfg, c).execute("chatwoot_search_contacts", {"credential":"atendimento","account_id":17,"inbox_id":4,"q":"cliente"}))
    assert result["error"]["code"] == "scope_denied"


def test_unknown_outcome_on_http_201_invalid_json(plugin, cfg):
    class APIError(Exception):
        status_http = 201
    class Failing(FakeClient):
        def send_text(self, a, c, message):
            self.calls.append(("messages.send_text", a, c))
            raise APIError("bad JSON")
    c = Failing()
    result = invoke(service(plugin, cfg, c), "chatwoot_send_public_message", content="Olá")
    assert result["error"]["code"] == "outcome_unknown"
    assert [call[0] for call in c.calls] == ["conversation.get", "messages.send_text"]


def test_contact_schema_is_closed_only_at_fields(plugin):
    from hermes_chatwoot_v02_tests.schemas import SCHEMAS
    props = SCHEMAS["chatwoot_update_contact"]["parameters"]["properties"]["fields"]
    assert props["additionalProperties"] is False
    assert props["properties"]["custom_attributes"]["type"] == ["object", "null"]


@pytest.mark.parametrize("fields", [{"blocked": 1}, {"name": []}, {"additional_attributes": []}, {"phone_number": 123}])
def test_invalid_contact_types_before_http(plugin, cfg, fields):
    c = FakeClient()
    result = invoke(service(plugin, cfg, c), "chatwoot_update_contact", fields=fields)
    assert result["error"]["code"] in ("invalid_arguments", "operation_denied")
    assert not c.calls
