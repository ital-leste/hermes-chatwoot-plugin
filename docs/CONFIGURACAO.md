# Configuração e permissões

O plugin lê as configurações do seu próprio namespace via `ctx.get_config("installations")`; não busca configurações globalmente nem lê `.env` por conta própria. O catálogo abaixo é **a configuração suportada na v0.1**.

```yaml
plugins:
  enabled: [chatwoot-tools]
  entries:
    chatwoot-tools:
      settings:
        installations:
          principal:
            base_url: "https://chatwoot.exemplo.com"
            token_env: "HERMES_CHATWOOT_PRINCIPAL_TOKEN"
            allowed_account_ids: [17]
            allowed_inbox_ids: [4, 6]
            allowed_operations:
              conversation.read: true
              messages.read: true
              messages.send_public: true
              # messages.send_private: true
              conversation.status.update: true
              conversation.labels.add: true
              conversation.labels.remove: true
```

### Campos da instalação

| Nome | Obrigatório | Semântica |
| --- | --- | --- |
| `base_url` | Sim | URL base http(s) sem credenciais, fragmento ou query. HTTPS recomendado fora do loopback. |
| `token_env` | Sim | Nome da credencial resolvida com `agent.secret_scope.get_secret`. |
| `allowed_account_ids` | Sim | Lista não vazia de inteiros positivos, únicos. |
| `allowed_inbox_ids` | Não | Se ausente, nenhuma restrição adicional; se `[]`, todas as conversas bloqueadas; se não vazia, guarda real com `conversations.get()`. |
| `allowed_operations` | Não | Mapa `permissão: true|false`; ausência permite zero operações. |

Cada instalação é um alias `[A-Za-z][A-Za-z0-9_-]*` com até 64 caracteres. Nomes de credenciais seguem o padrão de variáveis de ambiente maiúsculas. A ausência de credencial bloqueia a execução, mas não impede o registro estático das ferramentas.

### Operações da v0.1

| Configuração | Ferramenta |
| --- | --- |
| `conversation.read` | `chatwoot_get_conversation` |
| `messages.read` | `chatwoot_list_messages` |
| `messages.send_public` | `chatwoot_send_public_message` |
| `messages.send_private` | `chatwoot_send_private_note` |
| `conversation.status.update` | `chatwoot_set_status` |
| `conversation.labels.add` | `chatwoot_add_labels` |
| `conversation.labels.remove` | `chatwoot_remove_labels` |

Comentar/remover uma linha, ou trocar `true` por `false`, nega a operação. Por exemplo, `# messages.send_private: true` é equivalente a não declará-la. Valores não booleanos (`"true"`, `1`, `null` etc.) são erros. **Chaves desconhecidas são erro de configuração**, não passam silenciosamente. Não existe flag coringa de acesso total.

### Contatos e campos de atualização

Campos como `name`, `email` e `phone_number` **não podem ser escritos pela v0.1**, pois ainda não há ferramentas de contatos. Em uma versão futura, a política seguirá a mesma presença explícita de `true`:

```yaml
# Exemplo FUTURO — ainda NÃO incluir em uma configuração v0.1:
# allowed_operations:
#   contacts.update: true
# writable_contact_fields:
#   name: true
#   phone_number: true
#   email: false
```

A configuração da v0.1 rejeita `contacts.update` e `writable_contact_fields` como chaves ainda não suportadas. Assim, ninguém confundirá uma futura intenção declarativa com autorização implementada.

### Garantias e limites

- O agente não escolhe `base_url`, `token_env` ou valores de token em tool calls; somente `installation` nomeia um destino configurado.
- O Chatwoot também aplica as permissões reais associadas ao token. As políticas do plugin **restringem**, não ampliam, essas permissões.
- Uma inbox permitida não prova que a conversa era o destinatário pretendido. O consumidor define essa lógica.
- Existe uma pequena janela entre o GET de guarda e a escrita; essa verificação não é transacional. O token deve ter privilégio mínimo e o consumidor deve aplicar suas próprias garantias quando precisar de exclusividade.
- O token é retornado apenas ao construtor de `CWClient`; não é exposto ao modelo, ao JSON de sucesso ou a logs do plugin.
- Alterações de configuração são validadas na execução seguinte; reinicialização do Hermes pode ser necessária para atualizar configurações carregadas pelo gateway, conforme a versão do framework.
