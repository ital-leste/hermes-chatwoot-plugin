"""Esquemas JSON de ferramentas; uma única fonte para registro e manifesto."""
from __future__ import annotations

BASE = {
    "installation": {"type": "string", "description": "Alias da instalação configurada no Hermes."},
    "account_id": {"type": "integer", "minimum": 1, "description": "ID da conta no Chatwoot."},
    "conversation_id": {"type": "integer", "minimum": 1, "description": "ID da conversa na conta indicada."},
}


def schema(name: str, description: str, extra: dict | None = None, required: list[str] | None = None) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {**BASE, **(extra or {})},
            "required": [*BASE, *(required or [])],
            "additionalProperties": False,
        },
    }


SCHEMAS = {
    "chatwoot_get_conversation": schema(
        "chatwoot_get_conversation", "Consultar os dados de uma conversa de uma instalação Chatwoot autorizada."
    ),
    "chatwoot_list_messages": schema(
        "chatwoot_list_messages", "Ler mensagens de uma conversa. before/after são cursores opcionais.",
        {"before": {"type": "integer", "minimum": 0}, "after": {"type": "integer", "minimum": 0}},
    ),
    "chatwoot_send_public_message": schema(
        "chatwoot_send_public_message", "Publicar mensagem pública na conversa informada; não comprova entrega no canal externo.",
        {"content": {"type": "string", "minLength": 1}}, ["content"],
    ),
    "chatwoot_send_private_note": schema(
        "chatwoot_send_private_note", "Adicionar nota privada à conversa; não é mensagem pública ao contato.",
        {"content": {"type": "string", "minLength": 1}}, ["content"],
    ),
    "chatwoot_set_status": schema(
        "chatwoot_set_status", "Alterar status da conversa. snoozed_until só cabe com snoozed (timestamp Unix).",
        {"status": {"type": "string", "enum": ["open", "pending", "resolved", "snoozed"]},
         "snoozed_until": {"type": "integer", "minimum": 1}}, ["status"],
    ),
    "chatwoot_add_labels": schema(
        "chatwoot_add_labels", "Adicionar etiquetas sem substituir as outras; operações concorrentes não são atômicas.",
        {"labels": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}}, ["labels"],
    ),
    "chatwoot_remove_labels": schema(
        "chatwoot_remove_labels", "Remover apenas as etiquetas informadas da conversa.",
        {"labels": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}}, ["labels"],
    ),
}
