"""Executa operações nomeadas usando exclusivamente o CWClient público."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
import json

from .client_factory import create_client, resolve_secret
from .config import parse_installations
from .errors import (
    ArgumentsError, AuthorizationError, ConfigurationError, CredentialsError,
    DependencyError, PluginError,
)
from .permissions import authorize, verify_conversation


TOOLS_TO_OPERATIONS = {
    "chatwoot_get_conversation": "conversation.read",
    "chatwoot_list_messages": "messages.read",
    "chatwoot_send_public_message": "messages.send_public",
    "chatwoot_send_private_note": "messages.send_private",
    "chatwoot_set_status": "conversation.status.update",
    "chatwoot_add_labels": "conversation.labels.add",
    "chatwoot_remove_labels": "conversation.labels.remove",
}
_BASE = {"installation", "account_id", "conversation_id"}
_OPTIONAL = {
    "chatwoot_get_conversation": set(),
    "chatwoot_list_messages": {"before", "after"},
    "chatwoot_send_public_message": {"content"},
    "chatwoot_send_private_note": {"content"},
    "chatwoot_set_status": {"status", "snoozed_until"},
    "chatwoot_add_labels": {"labels"},
    "chatwoot_remove_labels": {"labels"},
}
_REQUIRED = {
    "chatwoot_get_conversation": set(),
    "chatwoot_list_messages": set(),
    "chatwoot_send_public_message": {"content"},
    "chatwoot_send_private_note": {"content"},
    "chatwoot_set_status": {"status"},
    "chatwoot_add_labels": {"labels"},
    "chatwoot_remove_labels": {"labels"},
}
_WRITES = frozenset({
    "messages.send_public", "messages.send_private", "conversation.status.update",
    "conversation.labels.add", "conversation.labels.remove",
})


def _arguments(tool: str, raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or any(not isinstance(k, str) for k in raw):
        raise ArgumentsError("Os argumentos devem ser objeto JSON.")
    data = dict(raw)
    if (set(data) - _BASE - _OPTIONAL[tool] or
            not _BASE.issubset(data) or not _REQUIRED[tool].issubset(data)):
        raise ArgumentsError("Argumentos ausentes ou não reconhecidos.")
    alias = data["installation"]
    if not isinstance(alias, str) or not alias.strip():
        raise ArgumentsError("installation deve ser texto não vazio.")
    for key in ("account_id", "conversation_id"):
        if type(data[key]) is not int or data[key] <= 0:
            raise ArgumentsError(f"{key} deve ser inteiro positivo.")
    if tool == "chatwoot_list_messages":
        for key in ("before", "after"):
            if key in data and (type(data[key]) is not int or data[key] < 0):
                raise ArgumentsError(f"{key} deve ser inteiro não negativo.")
    if tool in ("chatwoot_send_public_message", "chatwoot_send_private_note"):
        if not isinstance(data["content"], str) or not data["content"].strip():
            raise ArgumentsError("content deve ser texto não vazio.")
    if tool == "chatwoot_set_status":
        if type(data["status"]) is not str or data["status"] not in {"open", "pending", "resolved", "snoozed"}:
            raise ArgumentsError("status deve ser open, pending, resolved ou snoozed.")
        if "snoozed_until" in data:
            if data["status"] != "snoozed" or type(data["snoozed_until"]) is not int or data["snoozed_until"] <= 0:
                raise ArgumentsError("snoozed_until exige status snoozed e timestamp positivo.")
    if tool in ("chatwoot_add_labels", "chatwoot_remove_labels"):
        labels = data["labels"]
        if not isinstance(labels, list) or not labels or any(not isinstance(v, str) or not v.strip() for v in labels):
            raise ArgumentsError("labels deve ser lista não vazia de strings.")
    return data


class ToolService:
    def __init__(
        self,
        settings_provider: Callable[[], object],
        *,
        secret_provider: Callable[[str], str | None] = resolve_secret,
        client_factory: Callable[[str, str], Any] = create_client,
    ) -> None:
        self.settings_provider = settings_provider
        self.secret_provider = secret_provider
        self.client_factory = client_factory

    def execute(self, tool: str, raw: object) -> str:
        """A interface de ferramenta Hermes retorna JSON textual, mesmo nos erros."""
        operation = TOOLS_TO_OPERATIONS.get(tool)
        if operation is None:
            return self._failure("unknown_tool", "Ferramenta não reconhecida.")
        try:
            data = _arguments(tool, raw)
            installations = parse_installations(self.settings_provider())
            alias = data["installation"]
            installation = installations.get(alias)
            if installation is None:
                raise AuthorizationError("Instalação não configurada.")
            authorize(installation, operation, data["account_id"])
            token = self.secret_provider(installation.token_env)
            if not isinstance(token, str) or not token.strip():
                raise CredentialsError("Credencial da instalação indisponível.")
            # Cada chamada usa a instalação resolvida, sem sessão global que possa
            # transportar credenciais ou estado de outra instalação.
            with self.client_factory(installation.base_url, token.strip()) as client:
                result = self._execute_client(client, tool, data, installation)
            return json.dumps({
                "success": True, "installation": alias, "operation": operation,
                "data": result,
            }, ensure_ascii=False, allow_nan=False)
        except PluginError as exc:
            return self._failure(exc.code, str(exc))
        except (ValueError, TypeError) as exc:
            # Erros de contrato do cliente não devem conter dados enviados.
            return self._failure("invalid_arguments", "A operação foi rejeitada pelo contrato Python.")
        except (ModuleNotFoundError, ImportError):
            return self._failure("client_unavailable", "O pacote chatwoot_client não está instalado no runtime Hermes.")
        except Exception as exc:
            # Mensagens de exceções HTTP podem conter URLs, headers e dados pessoais.
            status = getattr(exc, "status_http", None)
            if type(status) is int and 100 <= status <= 599:
                return self._failure("chatwoot_api_error", "A API Chatwoot rejeitou a operação.", status_http=status)
            if operation in _WRITES:
                return self._failure("outcome_unknown", "Falha na operação de escrita; não repetir automaticamente.")
            return self._failure("execution_error", "Falha ao executar a operação Chatwoot.")

    @staticmethod
    def _failure(code: str, message: str, **extras: Any) -> str:
        return json.dumps({"success": False, "error": {"code": code, "message": message, **extras}}, ensure_ascii=False)

    @staticmethod
    def _execute_client(client: Any, tool: str, data: dict[str, Any], installation: Any) -> Any:
        aid, cid = data["account_id"], data["conversation_id"]
        conversation: Any = None
        # Se há restrição de inbox, todos os acessos ao recurso precisam
        # comprovar sua associação real, não apenas um inbox_id do agente.
        if installation.inbox_ids is not None or tool == "chatwoot_get_conversation":
            conversation = verify_conversation(
                client.conversations.get(aid, cid), account_id=aid,
                conversation_id=cid, installation=installation,
            )
        if tool == "chatwoot_get_conversation":
            return conversation
        if tool == "chatwoot_list_messages":
            return client.messages.list(aid, cid, **{
                k: data[k] for k in ("before", "after") if k in data
            })
        if tool in ("chatwoot_send_public_message", "chatwoot_send_private_note"):
            from chatwoot_client import TextMessage
            return client.messages.send_text(aid, cid, TextMessage(
                data["content"], private=(tool == "chatwoot_send_private_note")
            ))
        if tool == "chatwoot_set_status":
            from chatwoot_client import ConversationStatus
            kw = {"snoozed_until": data["snoozed_until"]} if "snoozed_until" in data else {}
            return client.conversations.set_status(aid, cid, ConversationStatus(data["status"]), **kw)
        if tool == "chatwoot_add_labels":
            return client.conversation_labels.add(aid, cid, data["labels"])
        if tool == "chatwoot_remove_labels":
            return client.conversation_labels.remove(aid, cid, data["labels"])
        raise ArgumentsError("Ferramenta não implementada.")
