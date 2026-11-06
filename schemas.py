"""Contratos JSON Schema das ferramentas Chatwoot apresentadas ao Hermes."""
from __future__ import annotations

CREDENTIAL = {"credential": {"type": "string", "minLength": 1, "description": "Identificador de credencial autorizada do perfil, nunca o token."}}
ACCOUNT = {"account_id": {"type": "integer", "minimum": 1, "description": "ID explícito da conta Chatwoot."}}
INBOX = {"inbox_id": {"type": "integer", "minimum": 1, "description": "ID explícito da inbox."}}
CONVERSATION = {"conversation_id": {"type": "integer", "minimum": 1, "description": "ID da conversa, conferido com conta e inbox."}}
CONTACT = {"contact_id": {"type": "integer", "minimum": 1, "description": "ID do contato, conferido com conta e inbox."}}


def schema(name: str, description: str, *, identity: dict, extra: dict | None = None, required: tuple[str, ...] = ()):
    return {"name": name, "description": description, "parameters": {
        "type": "object", "properties": {**CREDENTIAL, **ACCOUNT, **INBOX, **identity, **(extra or {})},
        "required": [*CREDENTIAL, *ACCOUNT, *INBOX, *identity, *required],
        "additionalProperties": False,
    }}


# Os tipos abaixo seguem a dataclass Contact do SDK. O schema orienta o
# provedor; a validação Python (inclusive a permissão por campo) é autoritativa.
CONTACT_TEXT = {"type": ["string", "null"], "minLength": 1, "pattern": r"\S"}
CONTACT_FIELDS = {
    "type": "object", "minProperties": 1, "additionalProperties": False,
    "description": "Somente campos de Contact; adicionalmente sujeitos a writable_contact_fields.",
    "properties": {
        "name": {**CONTACT_TEXT, "maxLength": 255},
        "email": {**CONTACT_TEXT, "pattern": r"^[^@\s]+@[^@\s]+(?![\s\S])"},
        "phone_number": {**CONTACT_TEXT, "pattern": r"^\+[1-9]\d{1,14}(?![\s\S])"},
        "identifier": dict(CONTACT_TEXT),
        "blocked": {"type": "boolean"},
        "avatar_url": dict(CONTACT_TEXT),
        # Estas propriedades sao mapas livres. Nao proibir chaves de negocio.
        "additional_attributes": {"type": ["object", "null"], "additionalProperties": True},
        "custom_attributes": {"type": ["object", "null"], "additionalProperties": True},
    },
}

SCHEMAS = {
    "chatwoot_get_conversation": schema("chatwoot_get_conversation", "Consultar conversa apos validar a triade conta/inbox/conversa.", identity=CONVERSATION),
    "chatwoot_list_conversations": schema("chatwoot_list_conversations", "Listar conversas da inbox com filtros opcionais.", identity={}, extra={
        "status": {"type":"string", "enum":["all", "open", "pending", "resolved", "snoozed"]},
        "q": {"type":"string", "minLength":1}, "page": {"type":"integer", "minimum":1},
    }),
    "chatwoot_list_messages": schema("chatwoot_list_messages", "Consultar mensagens com JSON nativo integral apos verificar a conversa.", identity=CONVERSATION, extra={
        "before": {"type":"integer", "minimum":0}, "after": {"type":"integer", "minimum":0},
    }),
    "chatwoot_send_public_message": schema("chatwoot_send_public_message", "Publicar texto na conversa validada; HTTP nao comprova entrega ao canal.", identity=CONVERSATION, extra={"content": {"type":"string", "minLength":1}}, required=("content",)),
    "chatwoot_send_private_note": schema("chatwoot_send_private_note", "Criar nota privada na conversa validada.", identity=CONVERSATION, extra={"content": {"type":"string", "minLength":1}}, required=("content",)),
    "chatwoot_send_media": schema("chatwoot_send_media", "Enviar imagem, documento, video ou audio publico por URL HTTPS de dominio explicitamente autorizado; nao aceitar caminhos locais. Para audio OGG de voz, is_voice_message=true.", identity=CONVERSATION, extra={
        "media_url": {"type": "string", "minLength": 1, "maxLength": 4096, "pattern": "^https://"},
        "mime_type": {"type": "string", "enum": ["image/png", "image/jpeg", "image/webp", "image/gif", "application/pdf", "video/mp4", "video/webm", "audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4"]},
        "filename": {"type": "string", "minLength": 1, "maxLength": 255},
        "caption": {"type": "string", "maxLength": 4000},
        "is_voice_message": {"type": "boolean"},
    }, required=("media_url", "mime_type", "filename")),
    "chatwoot_set_status": schema("chatwoot_set_status", "Alterar status da conversa validada.", identity=CONVERSATION, extra={
        "status": {"type":"string", "enum":["open", "pending", "resolved", "snoozed"]},
        "snoozed_until": {"type":"integer", "minimum":1},
    }, required=("status",)),
    "chatwoot_add_labels": schema("chatwoot_add_labels", "Acrescentar etiquetas sem substituir as demais (GET+POST nao atomico).", identity=CONVERSATION, extra={
        "labels":{"type":"array", "items":{"type":"string","minLength":1},"minItems":1},
    }, required=("labels",)),
    "chatwoot_remove_labels": schema("chatwoot_remove_labels", "Remover etiquetas selecionadas (GET+POST nao atomico).", identity=CONVERSATION, extra={
        "labels":{"type":"array", "items":{"type":"string","minLength":1},"minItems":1},
    }, required=("labels",)),
    "chatwoot_search_contacts": schema("chatwoot_search_contacts", "Pesquisar contatos com vinculacao comprovada a inbox.", identity={}, extra={
        "q":{"type":"string", "minLength":1}, "page":{"type":"integer", "minimum":1},
    }, required=("q",)),
    "chatwoot_get_contact": schema("chatwoot_get_contact", "Consultar contato associado a inbox.", identity=CONTACT),
    "chatwoot_get_contact_conversations": schema("chatwoot_get_contact_conversations", "Listar conversas do contato filtrando a inbox.", identity=CONTACT),
    "chatwoot_update_contact": schema("chatwoot_update_contact", "Atualizar campos tipados autorizados no perfil; edicao afeta o contato de toda a conta.", identity=CONTACT, extra={
        "fields": CONTACT_FIELDS,
    }, required=("fields",)),
}
