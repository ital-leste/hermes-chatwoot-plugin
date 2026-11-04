from __future__ import annotations
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def plugin(monkeypatch):
    name = "hermes_chatwoot_v02_tests"
    for item in list(sys.modules):
        if item == name or item.startswith(name + "."):
            monkeypatch.delitem(sys.modules, item, raising=False)
    spec = importlib.util.spec_from_file_location(name, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, mod)
    spec.loader.exec_module(mod)
    fake = types.ModuleType("chatwoot_client")
    class TextMessage:
        def __init__(self, content, private=False):
            if not content.strip(): raise ValueError("empty")
            self.content, self.private = content, private
    class Contact:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            if "phone_number" in kwargs and kwargs["phone_number"] is not None and not kwargs["phone_number"].startswith("+"):
                raise ValueError("invalid phone")
    class ConversationStatus(str):
        pass
    fake.TextMessage, fake.Contact, fake.ConversationStatus = TextMessage, Contact, ConversationStatus
    monkeypatch.setitem(sys.modules, "chatwoot_client", fake)
    return mod


class FakeClient:
    def __init__(self, *, inbox=4, cid=482, contact_inboxes=(4,), fail=None, search_items=None, conversations=None):
        self.inbox = inbox
        self.cid = cid
        self.contact_inboxes = contact_inboxes
        self.fail = fail
        self.calls = []
        self.closed = False
        self.conversations = SimpleNamespace(get=self.get_conversation, list=self.list_conversations, set_status=self.set_status)
        self.contacts = SimpleNamespace(get=self.get_contact, list_conversations=self.contact_conversations,
                                        search=self.search_contacts, update=self.update_contact)
        self.messages = SimpleNamespace(list=self.list_messages, send_text=self.send_text)
        self.conversation_labels = SimpleNamespace(add=self.add_labels, remove=self.remove_labels)
        self.search_items = search_items if search_items is not None else [{"id":25,"name":"Cliente"}]
        self._conversations = conversations if conversations is not None else [{"id":482,"account_id":17,"inbox_id":4}]

    def __enter__(self): return self
    def __exit__(self,*a): self.closed=True
    def _fail(self):
        if self.fail is not None:
            raise self.fail

    def get_conversation(self,a,c):
        self.calls.append(("conversation.get",a,c))
        self._fail()
        return {"id":self.cid, "inbox_id":self.inbox, "account_id":a,"sensitive": {"raw":"kept"}}

    def list_conversations(self,a,**kw):
        self.calls.append(("conversations.list",a,kw))
        return {"data":{"meta":{"total":1},"payload":self._conversations}}

    def list_messages(self,a,c,**kw):
        self.calls.append(("messages.list",a,c,kw))
        return {"payload":[{"id":71,"content":"mensagem integral","sender":{"phone":"+5511999"}}]}

    def send_text(self,a,c,message):
        self.calls.append(("messages.send_text",a,c,message.content,message.private))
        self._fail()
        return {"id":71,"content":message.content,"sender":{"phone":"+5511999"}}

    def set_status(self,a,c,status,**kw):
        self.calls.append(("conversations.set_status",a,c,status,kw));return {"status":status}

    def add_labels(self,a,c,l):
        self.calls.append(("labels.add",a,c,l));return {"payload":l}

    def remove_labels(self,a,c,l):
        self.calls.append(("labels.remove",a,c,l));return {"payload":l}

    def get_contact(self,a,contact_id):
        self.calls.append(("contacts.get",a,contact_id))
        return {"id":contact_id,"name":"Cliente","contact_inboxes":[{"inbox":{"id":i}} for i in self.contact_inboxes]}

    def contact_conversations(self,a,contact_id):
        self.calls.append(("contacts.list_conversations",a,contact_id))
        return {"payload":[{"id":482,"inbox_id":4},{"id":483,"inbox_id":8}]}

    def search_contacts(self,a,**kw):
        self.calls.append(("contacts.search",a,kw))
        return {"payload":self.search_items,"meta":{"page":1}}

    def update_contact(self,a,contact_id,contact):
        self.calls.append(("contacts.update",a,contact_id,contact.kwargs))
        return {"id":contact_id,"updated":contact.kwargs}


@pytest.fixture
def cfg():
    return {"base_url":"https://chatwoot.exemplo.com", "allowed_operations": {
        "conversation.read":True,"conversation.list":True,"messages.read":True,
        "messages.send_public":True,"messages.send_private":False,
        "conversation.status.update":True,"conversation.labels.add":True,
        "conversation.labels.remove":True,"contacts.search":True,
        "contacts.read":True,"contacts.conversations.read":True,"contacts.update":True},
        "writable_contact_fields":{"name":True,"phone_number":True,"email":False}}


@pytest.fixture
def factory():
    f=SimpleNamespace(clients=[],urls=[])
    def make(url, token):
        c=FakeClient();f.clients.append(c);f.urls.append((url,token));return c
    f.make=make
    return f


@pytest.fixture
def svc(plugin, cfg, factory):
    from hermes_chatwoot_v02_tests.chatwoot_tools.service import ToolService
    return ToolService(lambda:cfg, secret_provider=lambda _:"token_value", client_factory=factory.make)
