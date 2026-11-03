# Catálogo de ferramentas v0.1

Todas as ferramentas exigem os argumentos `installation: str`, `account_id: int` e `conversation_id: int`, com IDs positivos. Não aceitam `base_url`, `token` ou outros argumentos não documentados. O cliente Python fornece os contratos de domínio; o plugin não cria modelos alternativos de saída do Chatwoot.

| Ferramenta | Argumentos adicionais | Operação do pacote `chatwoot_client` |
| --- | --- | --- |
| `chatwoot_get_conversation` | — | `conversations.get(account_id, conversation_id)` |
| `chatwoot_list_messages` | `before?: int>=0`, `after?: int>=0` | `messages.list(account_id, conversation_id, before=..., after=...)` |
| `chatwoot_send_public_message` | `content: str` não vazio | `messages.send_text(account_id, conversation_id, TextMessage(content))` |
| `chatwoot_send_private_note` | `content: str` não vazio | `messages.send_text(account_id, conversation_id, TextMessage(content, private=True))` |
| `chatwoot_set_status` | `status: open\|pending\|resolved\|snoozed`; `snoozed_until?: int>0` somente com `snoozed` | `conversations.set_status(..., ConversationStatus(...), snoozed_until=...)` |
| `chatwoot_add_labels` | `labels: list[str]` não vazia | `conversation_labels.add(account_id, conversation_id, labels)` |
| `chatwoot_remove_labels` | `labels: list[str]` não vazia | `conversation_labels.remove(account_id, conversation_id, labels)` |

O campo `snoozed_until` é um timestamp Unix positivo. A regra de `ConversationStatus` pertence ao cliente tipado. `before=0` e `after=0` são cursores aceitos pelo contrato HTTP do cliente.

## Resultado bem-sucedido

Os handlers devolvem **texto JSON** (exigência do registro de ferramentas Hermes). Exemplo meramente ilustrativo:

```json
{
  "success": true,
  "installation": "principal",
  "operation": "messages.send_public",
  "data": {"id": 91}
}
```

`data` é a resposta **nativa** recebida do método da biblioteca Python, e pode ser objeto, lista ou `null` quando o endpoint não devolve corpo. Nenhum objeto `httpx.Response` é retornado. O envelope do plugin não deve ser interpretado como confirmação de entrega por WhatsApp.

## Resultado negado ou falho

```json
{"success": false, "error": {"code": "operation_denied", "message": "Operação não autorizada nesta instalação."}}
```

Códigos previstos: `invalid_arguments`, `invalid_configuration`, `operation_denied`, `scope_denied`, `credentials_unavailable`, `client_unavailable`, `chatwoot_api_error`, `execution_error`, `outcome_unknown`, `unknown_tool`.

Não são propagados tokens, headers, bodies HTTP nem mensagens de exceções de bibliotecas ao LLM. `chatwoot_api_error` pode incluir `status_http`. Erros sem status durante escrita são `outcome_unknown` e devem ser reconciliados antes de qualquer retentativa, pois o servidor pode já ter concluído a ação.

## Operações não incluídas

O cliente possui dezenas de outros recursos, mas a v0.1 **não** expõe mídias, contatos, criação de conversas, usuários, campanhas, webhooks, administração, atualização genérica nem exclusões. Não existe ferramenta genérica de acesso irrestrito à API; novos recursos devem ganhar esquema e permissão explícitos.
