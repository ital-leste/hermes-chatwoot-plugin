"""Contratos JSON Schema apresentados ao agente Hermes."""
from __future__ import annotations

ACCOUNT = {"account_id": {"type": "integer", "minimum": 1, "description": "ID da conta Chatwoot."}}
INBOX = {"inbox_id": {"type": "integer", "minimum": 1, "description": "ID da inbox dentro da conta."}}
CONVERSATION = {"conversation_id": {"type": "integer", "minimum": 1, "description": "ID da conversa; associação com a inbox será verificada."}}
CONTACT = {"contact_id": {"type": "integer", "minimum": 1, "description": "ID do contato na conta."}}


def schema(name: str, description: str, *, identity: dict, extra: dict | None = None, required: tuple[str, ...] = ()):  # noqa: E501
    return {"name": name, "description": description, "parameters": {
        "type": "object", "properties": {**ACCOUNT, **INBOX, **identity, **(extra or {})},
        "required": [*ACCOUNT, *INBOX, *identity, *required], "additionalProperties": False,
    }}


SCHEMAS = {
    "chatwoot_get_conversation": schema("chatwoot_get_conversation", "Consultar conversa após validar a tríade conta, inbox e conversa.", identity=CONVERSATION),
    "chatwoot_list_conversations": schema("chatwoot_list_conversations", "Listar conversas da inbox informada, com filtros opcionais.", identity={}, extra={
        "status": {"type":"string", "enum":["all", "open", "pending", "resolved", "snoozed"]},
        "q": {"type":"string", "minLength":1},
        "page": {"type":"integer", "minimum":1},
    }),
    "chatwoot_list_messages": schema("chatwoot_list_messages", "Consultar mensagens da conversa validada.", identity=CONVERSATION, extra={
        "before": {"type":"integer", "minimum":0}, "after": {"type":"integer", "minimum":0},
    }),
    "chatwoot_send_public_message": schema("chatwoot_send_public_message", "Publicar texto na conversa validada; não garante entrega externa.", identity=CONVERSATION, extra={"content": {"type":"string", "minLength":1}}, required=("content",)),
    "chatwoot_send_private_note": schema("chatwoot_send_private_note", "Criar nota privada na conversa validada.", identity=CONVERSATION, extra={"content": {"type":"string", "minLength":1}}, required=("content",)),
    "chatwoot_set_status": schema("chatwoot_set_status", "Alterar status da conversa validada.", identity=CONVERSATION, extra={
        "status": {"type":"string", "enum":["open", "pending", "resolved", "snoozed"]},
        "snoozed_until": {"type":"integer", "minimum":1},
    }, required=("status",)),
    "chatwoot_add_labels": schema("chatwoot_add_labels", "Acrescentar etiquetas sem substituir as existentes (GET+POST não atômico).", identity=CONVERSATION, extra={
        "labels":{"type":"array", "items":{"type":"string","minLength":1},"minItems":1},
    }, required=("labels",)),
    "chatwoot_remove_labels": schema("chatwoot_remove_labels", "Remover etiquetas selecionadas (GET+POST não atômico).", identity=CONVERSATION, extra={
        "labels":{"type":"array", "items":{"type":"string","minLength":1},"minItems":1},
    }, required=("labels",)),
    "chatwoot_search_contacts": schema("chatwoot_search_contacts", "Pesquisar contatos com associação verificável à inbox especificada.", identity={}, extra={
        "q":{"type":"string", "minLength":1}, "page":{"type":"integer", "minimum":1},
    }, required=("q",)),
    "chatwoot_get_contact": schema("chatwoot_get_contact", "Consultar contato associado à inbox informada.", identity=CONTACT),
    "chatwoot_get_contact_conversations": schema("chatwoot_get_contact_conversations", "Listar conversas de um contato limitadas à inbox indicada.", identity=CONTACT),
    "chatwoot_update_contact": schema("chatwoot_update_contact", "Atualizar somente campos expressamente autorizados no perfil; alteração afeta o contato da conta inteira.", identity=CONTACT, extra={
        "fields": {"type":"object", "minProperties":1, "description":"Campos de Contact autorizados em writable_contact_fields."},
    }, required=("fields",)),
}
