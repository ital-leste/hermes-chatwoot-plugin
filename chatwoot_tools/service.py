"""Valida ferramentas, resolve conexão e executa operações pelo SDK público."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from .config import WRITABLE_FIELDS, parse_config
from .connection import create_client, resolve_connection, resolve_secret
from .errors import ArgumentsError, AuthorizationError, PluginError, ScopeError
from .permissions import require_fields, require_operation
from .validators import contact_identity, conversation_identity
from .operations import contacts, conversations, labels, messages

TOOLS_TO_OPERATIONS = {
    "chatwoot_get_conversation": "conversation.read",
    "chatwoot_list_conversations": "conversation.list",
    "chatwoot_list_messages": "messages.read",
    "chatwoot_send_public_message": "messages.send_public",
    "chatwoot_send_private_note": "messages.send_private",
    "chatwoot_send_media": "messages.send_media",
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
    "chatwoot_send_private_note", "chatwoot_send_media", "chatwoot_set_status", "chatwoot_add_labels", "chatwoot_remove_labels",
})
_CONTACT = frozenset({"chatwoot_get_contact", "chatwoot_get_contact_conversations", "chatwoot_update_contact"})
_WRITES = frozenset({
    "messages.send_public", "messages.send_private", "messages.send_media", "conversation.status.update",
    "conversation.labels.add", "conversation.labels.remove", "contacts.update",
})
_OPTIONS = {
    "chatwoot_get_conversation": (set(), set()),
    "chatwoot_list_conversations": ({"status", "q", "page"}, set()),
    "chatwoot_list_messages": ({"before", "after"}, set()),
    "chatwoot_send_public_message": ({"content"}, {"content"}),
    "chatwoot_send_private_note": ({"content"}, {"content"}),
    "chatwoot_send_media": ({"media_url", "mime_type", "filename", "caption", "is_voice_message"}, {"media_url", "mime_type", "filename"}),
    "chatwoot_set_status": ({"status", "snoozed_until"}, {"status"}),
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
    optional, required = _OPTIONS[tool]
    if not (base | required).issubset(data) or set(data) - base - optional:
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
    if tool == "chatwoot_send_media":
        from urllib.parse import urlsplit
        from pathlib import PurePosixPath, PureWindowsPath
        import re
        mime_types = {"image/png", "image/jpeg", "image/webp", "image/gif",
                      "application/pdf", "video/mp4", "video/webm",
                      "audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4"}
        media_url, mime, filename = (
            data["media_url"], data["mime_type"], data["filename"]
        )
        if not isinstance(media_url, str) or len(media_url) > 4096:
            raise ArgumentsError("URL de midia invalida.")
        try:
            parsed = urlsplit(media_url)
            port = parsed.port
        except ValueError:
            raise ArgumentsError("URL de midia invalida.") from None
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username or parsed.password or parsed.fragment
                or port not in (None, 443)):
            raise ArgumentsError("Midia exige URL HTTPS sem credenciais.")
        if type(mime) is not str or mime not in mime_types:
            raise ArgumentsError("Tipo MIME nao autorizado.")
        if (type(filename) is not str or not 1 <= len(filename) <= 255
                or filename in (".", "..")
                or filename != PurePosixPath(filename).name
                or filename != PureWindowsPath(filename).name
                or any(ord(x) < 32 or ord(x) == 127 for x in filename)):
            raise ArgumentsError("Nome de anexo invalido.")
        if "caption" in data and (
            type(data["caption"]) is not str or len(data["caption"]) > 4000
        ):
            raise ArgumentsError("Legenda de midia invalida.")
        voice = data.get("is_voice_message", False)
        if type(voice) is not bool or (voice and mime != "audio/ogg"):
            raise ArgumentsError("Mensagem de voz exige audio/ogg.")
    if "status" in data:
        choices = {"all", "open", "pending", "resolved", "snoozed"} if tool == "chatwoot_list_conversations" else {"open", "pending", "resolved", "snoozed"}
        if type(data["status"]) is not str or data["status"] not in choices:
            raise ArgumentsError("Status inválido.")
    if "snoozed_until" in data and data.get("status") != "snoozed":
        raise ArgumentsError("snoozed_until requer status snoozed.")
    if "labels" in data:
        labels_input = data["labels"]
        if not isinstance(labels_input, list) or not labels_input or any(
            not isinstance(item, str) or not item.strip() for item in labels_input
        ):
            raise ArgumentsError("labels deve ser lista não vazia de strings.")
    if "fields" in data:
        fields = data["fields"]
        if not isinstance(fields, Mapping) or not fields or any(
            type(key) is not str or key not in WRITABLE_FIELDS for key in fields
        ):
            raise ArgumentsError("fields contém campo desconhecido ou está vazio.")
        # Falha antes da rede, mesmo quando o SDK estiver substituido por double.
        for key, value in fields.items():
            if key == "blocked":
                valid = type(value) is bool
            elif key in ("additional_attributes", "custom_attributes"):
                valid = value is None or isinstance(value, Mapping)
            else:
                valid = value is None or isinstance(value, str)
            if not valid:
                raise ArgumentsError("Tipo inválido em fields.")
        data["fields"] = dict(fields)
    return data


def _prepare_write(tool: str, data: dict[str, Any]) -> Any:
    """Prepara contratos do SDK antes de qualquer método potencialmente modificador."""
    if tool == "chatwoot_update_contact":
        from chatwoot_client import Contact
        contact = Contact(**data["fields"])
        contact.to_payload() if hasattr(contact, "to_payload") else None
        return contact
    if tool in ("chatwoot_send_public_message", "chatwoot_send_private_note"):
        from chatwoot_client import TextMessage
        return TextMessage(data["content"], private=(tool == "chatwoot_send_private_note"))
    if tool == "chatwoot_send_media":
        from chatwoot_client import Attachment, MediaMessage
        attachment = Attachment.from_url(
            data["media_url"], mime_type=data["mime_type"], filename=data["filename"]
        )
        return MediaMessage(
            attachments=[attachment], caption=data.get("caption"),
            private=False, is_voice_message=data.get("is_voice_message", False),
        )
    if tool == "chatwoot_set_status":
        from chatwoot_client import ConversationStatus
        return ConversationStatus(data["status"])
    return None


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
        # Significa somente que o método público pode ter tentado modificar dados.
        # Em etiquetas, o método do SDK faz GET e pode terminar sem POST.
        possible_write = False
        try:
            data = _arguments(tool, raw)
            config = parse_config(self.settings_provider())
            require_operation(config, operation)
            if tool == "chatwoot_update_contact":
                require_fields(config, data["fields"])
            credential = config.credentials.get(data["credential"])
            if credential is None:
                raise AuthorizationError("Identidade de usuário não autorizada neste perfil.")
            if data["account_id"] != credential.account_id:
                raise ScopeError("Conta não autorizada para a credencial selecionada.")
            if tool == "chatwoot_send_media":
                from urllib.parse import urlsplit
                if not config.media_allowed_hosts:
                    raise AuthorizationError("Envio de midia requer dominios de origem autorizados.")
                host = urlsplit(data["media_url"]).hostname
                if not host or host.lower().rstrip(".") not in config.media_allowed_hosts:
                    raise AuthorizationError("Dominio da midia nao autorizado.")
            prepared = _prepare_write(tool, data) if operation in _WRITES else None
            url, token = resolve_connection(config, credential, self.secret_provider)
            with self.client_factory(url, token) as cw:
                aid, iid = data["account_id"], data["inbox_id"]
                if tool in _CONVERSATION:
                    conversation = conversation_identity(cw, aid, iid, data["conversation_id"])
                    if tool == "chatwoot_get_conversation":
                        result = conversation
                    else:
                        possible_write = operation in _WRITES
                        result = self._run(cw, tool, data, prepared, allowed_hosts=config.media_allowed_hosts)
                elif tool in _CONTACT:
                    contact = contact_identity(cw, aid, iid, data["contact_id"])
                    if tool == "chatwoot_get_contact":
                        result = contact
                    else:
                        possible_write = operation in _WRITES
                        result = self._run(cw, tool, data, prepared)
                else:
                    result = self._run(cw, tool, data, prepared)
            return json.dumps({"success": True, "operation": operation, "credential": data["credential"], "data": result}, ensure_ascii=False, allow_nan=False)
        except PluginError as exc:
            if possible_write:
                return self._unknown()
            return self._error(exc.code, str(exc))
        except (ValueError, TypeError):
            if possible_write:
                return self._unknown()
            return self._error("invalid_arguments", "A operação foi rejeitada pelo contrato Python.")
        except (ModuleNotFoundError, ImportError):
            if possible_write:
                return self._unknown()
            return self._error("client_unavailable", "O pacote chatwoot_client não está disponível no runtime Hermes.")
        except Exception as exc:
            # Não retornar URLs, tokens, headers, corpos ou exceções ao modelo.
            status = getattr(exc, "status_http", None)
            if possible_write:
                # Só um conjunto restrito de status de rejeição comprovada
                # produz erro conhecido; 2xx inválido, 5xx e timeout são incertos.
                if type(status) is int and status in {400, 401, 403, 404, 405, 422}:
                    return self._error("chatwoot_api_error", "A API Chatwoot rejeitou a operação.", status_http=status)
                return self._unknown()
            if type(status) is int and 100 <= status <= 599:
                return self._error("chatwoot_api_error", "A consulta à API Chatwoot falhou.", status_http=status)
            return self._error("execution_error", "Falha ao consultar a API Chatwoot.")

    @classmethod
    def _unknown(cls) -> str:
        return cls._error("outcome_unknown", "Efeito da escrita indeterminado; reconciliar antes de repetir.")

    @staticmethod
    def _error(code: str, message: str, **extras: Any) -> str:
        return json.dumps({"success": False, "error": {"code": code, "message": message, **extras}}, ensure_ascii=False)

    @staticmethod
    def _run(cw: Any, tool: str, data: dict[str, Any], prepared: Any = None, *, allowed_hosts: frozenset[str] = frozenset()) -> Any:
        aid, iid = data["account_id"], data["inbox_id"]
        cid = data.get("conversation_id")
        contact_id = data.get("contact_id")
        if tool == "chatwoot_list_conversations":
            return conversations.list_conversations(cw, aid, iid, **{k: data[k] for k in ("status", "q", "page") if k in data})
        if tool == "chatwoot_list_messages":
            return messages.list_messages(cw, aid, cid, **{k: data[k] for k in ("before", "after") if k in data})
        if tool in ("chatwoot_send_public_message", "chatwoot_send_private_note"):
            return messages.send(cw, aid, cid, data["content"], tool == "chatwoot_send_private_note", prepared=prepared)
        if tool == "chatwoot_send_media":
            return messages.send_media(cw, aid, cid, prepared, allowed_hosts=allowed_hosts)
        if tool == "chatwoot_set_status":
            return conversations.set_status(cw, aid, cid, data["status"], data.get("snoozed_until"), prepared=prepared)
        if tool in ("chatwoot_add_labels", "chatwoot_remove_labels"):
            return labels.modify(cw, aid, cid, data["labels"], remove=tool == "chatwoot_remove_labels")
        if tool == "chatwoot_search_contacts":
            return contacts.search(cw, aid, iid, data["q"], data.get("page"))
        if tool == "chatwoot_get_contact_conversations":
            return contacts.list_conversations(cw, aid, iid, contact_id)
        if tool == "chatwoot_update_contact":
            return contacts.update(cw, aid, contact_id, prepared)
        raise ArgumentsError("Operação não implementada.")
