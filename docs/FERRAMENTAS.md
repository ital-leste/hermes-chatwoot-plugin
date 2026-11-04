# Contratos das ferramentas v0.2.0rc2

## Identidade

O plugin possui **uma instalação Chatwoot por perfil Hermes e pode utilizar vários tokens de usuário**. Não existe `installation`, `base_url` ou `api_token` como argumento das ferramentas. Toda ferramenta exige `credential: str` (identidade declarada em `credentials`), `account_id: int>0` e `inbox_id: int>0`. `credential` nunca é o token ou o nome da variável de ambiente.

Ferramentas de conversa também exigem `conversation_id: int>0`. Ferramentas de contato individual exigem `contact_id: int>0`. Os campos são obrigatórios inclusive quando há apenas uma conta/inbox no servidor.

| Ferramenta | Argumentos adicionais | Método do cliente |
| --- | --- | --- |
| `chatwoot_get_conversation` | `conversation_id` | `conversations.get` com guarda obrigatória |
| `chatwoot_list_conversations` | `status?`, `q?`, `page?` | `conversations.list(..., inbox_id=...)`; valida todos os itens |
| `chatwoot_list_messages` | `conversation_id`, `before?`, `after?` | `messages.list` após guarda da tríade |
| `chatwoot_send_public_message` | `conversation_id`, `content` | `messages.send_text(..., TextMessage(content))` |
| `chatwoot_send_private_note` | `conversation_id`, `content` | `messages.send_text(..., TextMessage(content, private=True))` |
| `chatwoot_set_status` | `conversation_id`, `status`, `snoozed_until?` | `conversations.set_status` com enum tipado |
| `chatwoot_add_labels` | `conversation_id`, `labels: list[str]` | `conversation_labels.add` |
| `chatwoot_remove_labels` | `conversation_id`, `labels: list[str]` | `conversation_labels.remove` |
| `chatwoot_search_contacts` | `q: str`, `page?` | `contacts.search`, conferência individual por inbox |
| `chatwoot_get_contact` | `contact_id` | `contacts.get`, conferência de vínculo com inbox |
| `chatwoot_get_contact_conversations` | `contact_id` | `contacts.list_conversations`, restringe itens à inbox |
| `chatwoot_update_contact` | `contact_id`, `fields: dict` | `contacts.update` com `Contact(**fields)` tipado |

Todos os resultados bem-sucedidos são texto JSON com `success`, `operation`, `credential`, `data`; o valor de `data` preserva os campos nativos retornados pela API (exceto exclusão de candidatos de outras inboxes nas buscas). O plugin não garante entrega do canal externo após publicação HTTP.

### Exemplo de publicação

```json
{"credential":"italbot","account_id":1,"inbox_id":4,"conversation_id":482,"content":"Bom dia!"}
```

### Exemplo de busca de contato

```json
{"credential":"italbot","account_id":1,"inbox_id":4,"q":"Maria","page":1}
```

### Exemplo de edição de contato

```json
{"credential":"italbot","account_id":1,"inbox_id":4,"contact_id":25,"fields":{"name":"Maria","phone_number":"+5511999999999"}}
```

Se `email` não estiver autorizado, a combinação `{"name":"Maria","email":"..."}` será rejeitada integralmente antes da escrita. `phone_number` precisa atender ao formato E.164 validado por `Contact` do cliente Python.

### Seleção de usuário

`credential: "italbot"`, `credential: "luiz"` e `credential: "marcio"` podem apontar para tokens diferentes da mesma instalação. `allowed_account_ids` limita quais contas cada token pode acessar no plugin. A API Chatwoot aplica as permissões reais do token e atribui a autoria segundo a identidade autenticada — a correspondência deve ser verificada em homologação. Alterar o nome do campo `credential` não altera a autoria no servidor. A v0.2rc2 não vincula automaticamente uma identidade de usuário a uma sessão de atendimento; o agente pode escolher qualquer uma das identidades que o perfil disponibiliza.

### Erros

`invalid_configuration`, `operation_denied`, `scope_denied`, `invalid_arguments`, `credentials_unavailable`, `client_unavailable`, `chatwoot_api_error`, `execution_error`, `outcome_unknown`, `unknown_tool`. Corpos de exceção e segredos não retornam ao modelo. `outcome_unknown` só é usado após o início de uma tentativa de escrita; consultas de guarda com falha não o geram.
