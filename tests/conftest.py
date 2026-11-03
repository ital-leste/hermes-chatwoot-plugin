"""Injeção do cliente falso; testes não fazem chamadas de rede ou VPS."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from enum import StrEnum
from dataclasses import dataclass

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def plugin():
    name = "hermes_chatwoot_plugin_tests"
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_chatwoot(monkeypatch):
    """Representa somente a interface pública relevante do client 0.1.0."""
    class ConversationStatus(StrEnum):
        OPEN = "open"
        PENDING = "pending"
        RESOLVED = "resolved"
        SNOOZED = "snoozed"

    @dataclass
    class TextMessage:
        content: str
        private: bool = False

    module = ModuleType("chatwoot_client")
    module.TextMessage = TextMessage
    module.ConversationStatus = ConversationStatus
    monkeypatch.setitem(sys.modules, "chatwoot_client", module)
    return module


class FakeClient:
    def __init__(self, *, inbox_id=4, account_id=17, conversation_id=42, fail=None):
        self.calls = []
        self.fail = fail
        self.inbox_id = inbox_id
        self.account_id = account_id
        self.conversation_id = conversation_id
        self.conversations = self
        self.messages = self
        self.conversation_labels = self
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def get(self, account_id, conversation_id):
        self.calls.append(("get", account_id, conversation_id))
        if self.fail:
            raise self.fail
        return {"id": self.conversation_id, "inbox_id": self.inbox_id, "account_id": self.account_id}

    def list(self, account_id, conversation_id, **kwargs):
        self.calls.append(("list", account_id, conversation_id, kwargs))
        return {"payload": [{"id": 70, "content": "Oi"}]}

    def send_text(self, account_id, conversation_id, message):
        self.calls.append(("send_text", account_id, conversation_id, message.content, message.private))
        if self.fail:
            raise self.fail
        return {"id": 91}

    def set_status(self, account_id, conversation_id, status, **kwargs):
        self.calls.append(("set_status", account_id, conversation_id, status, kwargs))
        return {"status": str(status)}

    def add(self, account_id, conversation_id, labels):
        self.calls.append(("add", account_id, conversation_id, labels))
        return {"payload": labels}

    def remove(self, account_id, conversation_id, labels):
        self.calls.append(("remove", account_id, conversation_id, labels))
        return {"payload": []}


@pytest.fixture
def factory():
    clients = []
    def create(url, token):
        client = FakeClient()
        clients.append((url, token, client))
        return client
    create.clients = clients
    return create


@pytest.fixture
def configured():
    return {
        "principal": {
            "base_url": "https://cw.example",
            "token_env": "CHATWOOT_MAIN_TOKEN",
            "allowed_account_ids": [17],
            "allowed_inbox_ids": [4, 6],
            "allowed_operations": {
                "conversation.read": True, "messages.read": True,
                "messages.send_public": True, "messages.send_private": False,
                "conversation.status.update": True,
                "conversation.labels.add": True, "conversation.labels.remove": True,
            },
        },
        "homolog": {
            "base_url": "http://127.0.0.1:3000",
            "token_env": "CHATWOOT_HOMOLOG_TOKEN",
            "allowed_account_ids": [1],
            "allowed_operations": {"messages.read": True},
        },
    }


@pytest.fixture
def service(plugin, configured, factory, fake_chatwoot):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.service import ToolService
    return ToolService(
        lambda: configured,
        secret_provider=lambda key: {"CHATWOOT_MAIN_TOKEN":"main-secret", "CHATWOOT_HOMOLOG_TOKEN":"homolog-secret"}.get(key),
        client_factory=factory,
    )
