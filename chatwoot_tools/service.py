"""Orquestra autorização, conexão confiável e operações tipadas do cliente."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
import json

from .config import parse_config, WRITABLE_FIELDS
from .connection import create_client, resolve_secret, resolve_connection
from .errors import ArgumentsError, AuthorizationError, ScopeError, PluginError
from .permissions import require_fields, require_operation
from .validators import conversation_identity, contact_identity
from .operations import contacts, conversations, labels, messages

TOOLS_TO_OPERATIONS = {
    "chatwoot_get_conversation": "conversation.read",
    "chatwoot_list_conversations": "conversation.list",
    "chatwoot_list_messages": "messages.read",
    "chatwoot_send_public_message": "messages.send_public",
    "chatwoot_send_private_note": "messages.send_private",
    "chatwoot_set_status": "conversation.status.update",
    "chatwoot_add_labels": "conversation.labels.add",
    "chatwoot_remove_labels": "conversation.labels.remove",
    "chatwoot_search_contacts": "contacts.search",
    "chatwoot_get_contact": "contacts.read",
    "chatwoot_get_contact_conversations": "contacts.conversations.read",
    "chatwoot_update_contact": "contacts.update",
}
_CONVERSATION = frozenset({
    "chatwoot_get_conversation", "chatwoot_list_messages", "chatwoot_send_public_message",
    "chatwoot_send_private_note", "chatwoot_set_status", "chatwoot_add_labels", "chatwoot_remove_labels",
})
_CONTACT = frozenset({"chatwoot_get_contact", "chatwoot_get_contact_conversations", "chatwoot_update_contact"})
_WRITES = frozenset({"messages.send_public", "messages.send_private", "conversation.status.update", "conversation.labels.add", "conversation.labels.remove", "contacts.update"})
_OPTIONS = {
    "chatwoot_get_conversation": (set(), set()),
    "chatwoot_list_conversations": ({"status","q","page"}, set()),
    "chatwoot_list_messages": ({"before", "after"}, set()),
    "chatwoot_send_public_message": ({"content"}, {"content"}),
    "chatwoot_send_private_note": ({"content"}, {"content"}),
    "chatwoot_set_status": ({"status","snoozed_until"}, {"status"}),
    "chatwoot_add_labels": ({"labels"}, {"labels"}),
    "chatwoot_remove_labels": ({"labels"}, {"labels"}),
    "chatwoot_search_contacts": ({"q", "page"}, {"q"}),
    "chatwoot_get_contact": (set(), set()),
    "chatwoot_get_contact_conversations": (set(), set()),
    "chatwoot_update_contact": ({"fields"}, {"fields"}),
}


def _arguments(tool: str, raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or any(type(k) is not str for k in raw):
        raise ArgumentsError("Argumentos devem ser objeto JSON.")
    data = dict(raw)
    base = {"credential", "account_id", "inbox_id"}
    if tool in _CONVERSATION:
        base.add("conversation_id")
    if tool in _CONTACT:
        base.add("contact_id")
    opt, req = _OPTIONS[tool]
    if not (base | req).issubset(data) or set(data) - base - opt:
        raise ArgumentsError("Argumentos ausentes ou não reconhecidos.")
    if not isinstance(data["credential"], str) or not data["credential"].strip():
        raise ArgumentsError("credential deve ser nome de identidade não vazio.")
    for key in base - {"credential"}:
        if type(data[key]) is not int or data[key] <= 0:
            raise ArgumentsError(f"{key} deve ser inteiro positivo.")
    for key in ("page", "before", "after", "snoozed_until"):
        if key in data and (type(data[key]) is not int or data[key] < (0 if key in ("before", "after") else 1)):
            raise ArgumentsError(f"{key} deve ser inteiro válido.")
    for key in ("q", "content"):
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            raise ArgumentsError(f"{key} deve ser texto não vazio.")
    if "status" in data:
        choices = {"all", "open", "pending", "resolved", "snoozed"} if tool == "chatwoot_list_conversations" else {"open", "pending", "resolved", "snoozed"}
        if type(data["status"]) is not str or data["status"] not in choices:
            raise ArgumentsError("Status inválido.")
    if "snoozed_until" in data and data.get("status") != "snoozed":
        raise ArgumentsError("snoozed_until requer status snoozed.")
    if "labels" in data:
        v = data["labels"]
        if not isinstance(v, list) or not v or any(not isinstance(x, str) or not x.strip() for x in v):
            raise ArgumentsError("labels deve ser lista não vazia de strings.")
    if "fields" in data:
        fields = data["fields"]
        if not isinstance(fields, Mapping) or not fields or any(type(k) is not str or k not in WRITABLE_FIELDS for k in fields):
            raise ArgumentsError("fields contém campo desconhecido ou está vazio.")
        data["fields"] = dict(fields)
    return data


class ToolService:
    def __init__(
        self, settings_provider: Callable[[], object], *,
        secret_provider: Callable[[str], str | None] = resolve_secret,
        client_factory: Callable[[str, str], Any] = create_client,
    ) -> None:
        self.settings_provider = settings_provider
        self.secret_provider = secret_provider
        self.client_factory = client_factory

    def execute(self, tool: str, raw: object) -> str:
        operation = TOOLS_TO_OPERATIONS.get(tool)
        if operation is None:
            return self._error("unknown_tool", "Ferramenta desconhecida.")
        write_started = False
        try:
            data = _arguments(tool, raw)
            cfg = parse_config(self.settings_provider())
            require_operation(cfg, operation)
            if tool == "chatwoot_update_contact":
                require_fields(cfg, data["fields"])
            credential = cfg.credentials.get(data["credential"])
            if credential is None:
                raise AuthorizationError("Identidade de usuário não autorizada neste perfil.")
            if data["account_id"] != credential.account_id:
                raise ScopeError("Conta não autorizada para a credencial selecionada.")
            url, token = resolve_connection(cfg, credential, self.secret_provider)
            with self.client_factory(url, token) as cw:
                aid, iid = data["account_id"], data["inbox_id"]
                if tool in _CONVERSATION:
                    # Confere sempre conta, inbox e conversa, independentemente de allowlists.
                    conversation = conversation_identity(cw, aid, iid, data["conversation_id"])
                    if tool == "chatwoot_get_conversation":
                        result = conversation
                    else:
                        if operation in _WRITES:
                            write_started = True
                        result = self._run(cw, tool, data)
                elif tool in _CONTACT:
                    contact = contact_identity(cw, aid, iid, data["contact_id"])
                    if tool == "chatwoot_get_contact":
                        result = contact
                    else:
                        if operation in _WRITES:
                            write_started = True
                        result = self._run(cw, tool, data)
                else:
                    result = self._run(cw, tool, data)
            return json.dumps({"success": True, "operation": operation, "credential": data["credential"], "data": result}, ensure_ascii=False, allow_nan=False)
        except PluginError as e:
            return self._error(e.code, str(e))
        except (ValueError, TypeError):
            return self._error("invalid_arguments", "A operação foi rejeitada pelo contrato Python.")
        except (ModuleNotFoundError, ImportError):
            return self._error("client_unavailable", "O pacote chatwoot_client não está disponível no runtime Hermes.")
        except Exception as e:
            # Não devolver corpo, headers, URL ou token ao modelo, mesmo em exceções.
            status = getattr(e, "status_http", None)
            if type(status) is int and 100 <= status <= 599:
                return self._error("chatwoot_api_error", "A API Chatwoot rejeitou a operação.", status_http=status)
            if write_started:
                return self._error("outcome_unknown", "Falha após início da escrita; reconciliar antes de repetir.")
            return self._error("execution_error", "Falha ao consultar a API Chatwoot.")

    @staticmethod
    def _error(code: str, message: str, **extras: Any) -> str:
        return json.dumps({"success": False, "error": {"code":code,"message":message,**extras}}, ensure_ascii=False)

    @staticmethod
    def _run(cw: Any, tool: str, data: dict[str, Any]) -> Any:
        aid, iid = data["account_id"], data["inbox_id"]
        cid = data.get("conversation_id")
        contact_id = data.get("contact_id")
        if tool == "chatwoot_list_conversations":
            return conversations.list_conversations(cw, aid, iid, **{k:data[k] for k in ("status","q","page") if k in data})
        if tool == "chatwoot_list_messages":
            return messages.list_messages(cw, aid, cid, **{k:data[k] for k in ("before","after") if k in data})
        if tool in ("chatwoot_send_public_message", "chatwoot_send_private_note"):
            return messages.send(cw, aid, cid, data["content"], tool == "chatwoot_send_private_note")
        if tool == "chatwoot_set_status":
            return conversations.set_status(cw, aid, cid, data["status"], data.get("snoozed_until"))
        if tool in ("chatwoot_add_labels", "chatwoot_remove_labels"):
            return labels.modify(cw, aid, cid, data["labels"], remove=tool=="chatwoot_remove_labels")
        if tool == "chatwoot_search_contacts":
            return contacts.search(cw, aid, iid, data["q"], data.get("page"))
        if tool == "chatwoot_get_contact_conversations":
            return contacts.list_conversations(cw, aid, iid, contact_id)
        if tool == "chatwoot_update_contact":
            return contacts.update(cw, aid, contact_id, data["fields"])
        raise ArgumentsError("Operação não implementada.")
