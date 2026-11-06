# Contratos das ferramentas v0.2.0rc5 — revisao G3

## Identidade

O plugin possui **uma instalação Chatwoot por perfil Hermes e pode utilizar vários tokens de usuário**. Não existe `installation`, `base_url` ou `api_token` como argumento das ferramentas. Toda ferramenta exige `credential: str` (identidade declarada em `credentials`), `account_id: int>0` e `inbox_id: int>0`. `credential` nunca é o token ou o nome da variável de ambiente.

Ferramentas de conversa também exigem `conversation_id: int>0`. Ferramentas de contato individual exigem `contact_id: int>0`. Os campos são obrigatórios inclusive quando há apenas uma conta/inbox no servidor.

| Ferramenta | Argumentos adicionais | Método do cliente |
| --- | --- | --- |
| `chatwoot_get_conversation` | `conversation_id` | `conversations.get` com guarda obrigatória |
| `chatwoot_list_conversations` | `status?`, `q?`, `page?` | `conversations.list(..., inbox_id=...)`; valida todos os itens |
| `chatwoot_list_messages` | `conversation_id`, `before?`, `after?`, `summary?` | `messages.list` após guarda; `summary=true` agrega páginas e IDs únicos |
| `chatwoot_send_public_message` | `conversation_id`, `content` | `messages.send_text(..., TextMessage(content))` |
| `chatwoot_send_private_note` | `conversation_id`, `content` | `messages.send_text(..., TextMessage(content, private=True))` |
| `chatwoot_set_status` | `conversation_id`, `status`, `snoozed_until?` | `conversations.set_status` com enum tipado |
| `chatwoot_add_labels` | `conversation_id`, `labels: list[str]` | `conversation_labels.add` |
| `chatwoot_remove_labels` | `conversation_id`, `labels: list[str]` | `conversation_labels.remove` |
| `chatwoot_search_contacts` | `q: str`, `page?` | `contacts.search`, conferência individual por inbox |
| `chatwoot_get_contact` | `contact_id` | `contacts.get`, conferência de vínculo com inbox |
| `chatwoot_get_contact_conversations` | `contact_id` | `contacts.list_conversations`, restringe itens à inbox |
| `chatwoot_update_contact` | `contact_id`, `fields: dict` | `contacts.update` com `Contact(**fields)` tipado |

Todos os resultados bem-sucedidos são texto JSON com `success`, `operation`, `credential`, `data`; por padrao `data` preserva o JSON nativo (exceto filtros de inbox). No modo `summary=true`, `data` e um resumo calculado pelo plugin, nao o envelope nativo. O plugin não garante entrega do canal externo após publicação HTTP.

### Contagem e primeira mensagem (G3)

`chatwoot_list_messages` sem `summary` preserva exatamente uma página da API. Para **contagem total verificável**, chamar com `summary=true`, sem `before` nem `after`. O plugin percorre até uma página vazia, deduplica pelo `id` e devolve `complete=true`, `unique_count`, `duplicate_count`, `pages_read`, `first_message_id`, `last_message_id` e `message_ids` em ordem crescente. Se a paginação não progredir, houver envelope inválido ou ultrapassar 100 páginas, retorna `pagination_incomplete` **sem contagem parcial de sucesso**. O resultado descreve a leitura realizada, não um snapshot transacional se a conversa mudar durante a varredura. Para conferir detalhes, usar a consulta de página normalmente.

```json
{"credential":"atendimento","account_id":7,"inbox_id":4,"conversation_id":482,"summary":true}
```

### Exemplo de publicação

```json
{"credential":"atendimento","account_id":7,"inbox_id":4,"conversation_id":482,"content":"Bom dia!"}
```

### Exemplo de busca de contato

```json
{"credential":"atendimento","account_id":7,"inbox_id":4,"q":"Maria","page":1}
```

### Exemplo de edição de contato

```json
{"credential":"atendimento","account_id":7,"inbox_id":4,"contact_id":25,"fields":{"name":"Maria","phone_number":"+5511999999999"}}
```

Se `email` não estiver autorizado, a combinação `{"name":"Maria","email":"..."}` será rejeitada integralmente antes da escrita. `phone_number` precisa atender ao formato E.164 validado por `Contact` do cliente Python.

### Seleção de usuário

`credential: "atendimento"`, `credential: "operador_a"` e `credential: "operador_b"` podem apontar para tokens diferentes da mesma instalação. `account_id` vincula a identidade selecionada a uma única conta e deve corresponder ao parâmetro explícito da ferramenta. A API Chatwoot aplica as permissões reais do token e atribui a autoria segundo a identidade autenticada — a correspondência deve ser verificada em homologação. Alterar o nome do campo `credential` não altera a autoria no servidor. A v0.2rc3 não vincula automaticamente uma identidade de usuário a uma sessão de atendimento; o agente pode escolher qualquer uma das identidades que o perfil disponibiliza.

### Erros

`invalid_configuration`, `operation_denied`, `scope_denied`, `invalid_arguments`, `credentials_unavailable`, `client_unavailable`, `chatwoot_api_error`, `execution_error`, `media_unavailable`, `media_redirect_rejected`, `pagination_incomplete`, `outcome_unknown`, `unknown_tool`. Corpos de exceção e segredos não retornam ao modelo. `outcome_unknown` indica que uma escrita **pode ter sido tentada** em um método potencialmente modificador. Isso não comprova transmissão: métodos de etiquetas podem terminar após GET sem POST. Consultas de guarda anteriores ao método não recebem esse marcador. Não repetir automaticamente; reconciliar resultados ambíguos.

### Envelope do lote vs. JSON da API

O envelope mínimo de mensagens agrupadas pertence ao **orquestrador/consumidor**. A consulta via plugin oferece `data` com JSON original para operações individuais, sem reduzir metadados, mensagens e atributos. Busca e histórico por inbox filtram *itens fora do escopo*, preservando os campos de cada item incluído. O filtro pode manter metadados de contagem anteriores à exclusão local. O modelo pode responder diretamente a um lote suficiente, sem consultas redundantes, mas a publicação requer executor único autorizado.

Campos de `chatwoot_update_contact.fields` são tipados (incluindo `null` em campos compatíveis) e autorizados por `writable_contact_fields`. `custom_attributes` e `additional_attributes` mantêm objetos livres; a validação Python do SDK rejeita valores não JSON e não finitos mesmo quando o provedor de schema não o faz.

**Mídia pré-POST:** redirecionamentos HTTPS (incluindo Active Storage) são rejeitados pelo SDK com `media_redirect_rejected`; usar a URL final HTTPS do host permitido. Download falho, excedente ou inválido resulta em `media_unavailable`. Ambos comprovam que não houve POST pelo fluxo do SDK. Erros após possível POST permanecem `outcome_unknown` e exigem reconciliação. Não registrar URLs assinadas.
