# Configuração e credenciais por perfil — v0.2.0rc2

O plugin utiliza um único servidor Chatwoot por perfil Hermes, mas pode autenticar vários usuários diferentes na mesma instalação, inclusive na mesma conta. As credenciais são gerenciadas pelo perfil, nunca por um arquivo do plugin.

## Arquivo `.env` do perfil Hermes

Exemplo em `~/.hermes/profiles/italbot/.env` (o caminho real deve ser confirmado na instalação Hermes):

```dotenv
CHATWOOT_BASE_URL=https://chatwoot.exemplo.com
CHATWOOT_ITALBOT_TOKEN=valor_italbot
CHATWOOT_LUIZ_TOKEN=valor_luiz
CHATWOOT_MARCIO_TOKEN=valor_marcio
```

Os valores são ilustrativos. Nunca versionar o arquivo com tokens reais. O plugin resolve URL/token usando `agent.secret_scope.get_secret`, que respeita o escopo de credenciais do perfil. Não lê o arquivo `.env` diretamente nem usa `os.getenv` como fallback que poderia escapar do perfil em gateways multiplexados.

## Arquivo `config.yaml` do perfil

```yaml
plugins:
  enabled:
    - chatwoot-tools
  entries:
    chatwoot-tools:
      settings:
        base_url_env: CHATWOOT_BASE_URL
        allow_insecure_http: false
        credentials:
          italbot:
            token_env: CHATWOOT_ITALBOT_TOKEN
            allowed_account_ids: [1, 2]
          luiz:
            token_env: CHATWOOT_LUIZ_TOKEN
            allowed_account_ids: [1]
          marcio:
            token_env: CHATWOOT_MARCIO_TOKEN
            allowed_account_ids: [2]
        allowed_operations:
          conversation.read: true
          conversation.list: true
          messages.read: true
          messages.send_public: true
          # messages.send_private: true
          conversation.status.update: true
          conversation.labels.add: true
          conversation.labels.remove: true
          contacts.search: true
          contacts.read: true
          contacts.conversations.read: true
          contacts.update: true
        writable_contact_fields:
          name: true
          phone_number: true
          # email: true
          # identifier: true
          # blocked: true
          # avatar_url: true
          # additional_attributes: true
          # custom_attributes: true
```

`base_url_env` contém o **nome** da variável com a URL. Cada identidade em `credentials` possui seu próprio `token_env` e uma lista não vazia de contas autorizadas. Nomes de variáveis devem ser válidos e distintos; não é permitido referenciar a mesma variável de token em duas identidades. Não há aliases de **instalações**, somente identificadores explícitos de **credenciais de usuários**.

As doze ferramentas exigem `credential`, por exemplo `credential: "luiz"`, além dos IDs de conta e inbox e, conforme a operação, do ID da conversa ou contato. O agente não fornece a URL, o nome da variável de ambiente ou o token. A seleção de uma identidade desconhecida ou não autorizada para a conta falha antes de qualquer chamada HTTP.

## Manutenção de usuários e tokens

- **Novo usuário:** cadastrar seu token no `.env` do perfil e incluir uma entrada em `credentials` com as contas autorizadas.
- **Rotação:** atualizar o valor da variável existente; nenhum arquivo de código do plugin precisa mudar.
- **Remoção:** excluir ou comentar a entrada do usuário em `credentials`. A tentativa de utilizar aquela identidade será rejeitada quando a configuração atualizada estiver ativa; revogar o token no Chatwoot se também for necessário impedir o uso por outros clientes.
- **Mudança de conta:** editar `allowed_account_ids` daquela identidade; a API Chatwoot também deve autorizar o usuário na conta indicada.
- **Mudança de servidor:** configurar outro perfil Hermes/ambiente, com sua própria URL e tokens; não há escolha arbitrária de servidor nos argumentos das ferramentas.

A configuração e o valor da variável de ambiente devem estar carregados no runtime real. Em um gateway de perfil único, editar `.env` pode exigir reinicialização do processo; em multiplexação o escopo pode ser atualizado em outro momento. Não presumir rotação instantânea até verificar o procedimento do Hermes instalado.

## Segurança e operações

- O operador autoriza uma lista de identidades no perfil. **O agente poderá escolher entre todas as identidades ali permitidas.** Essa seleção não é uma autorização específica de sessão ou de operador humano. Caso Luiz e Márcio não devam ser intercambiáveis em determinados atendimentos, separe os perfis ou implemente uma associação confiável de credencial por execução no consumidor.
- Todas as operações exigem `account_id` e `inbox_id`. Uma operação vinculada a conversa exige também `conversation_id`, conferindo a associação real antes de executar.
- `allowed_operations` e `writable_contact_fields` são mapas `nome: true`. Linhas ausentes/comentadas/`false` negam a operação/campo. Nomes desconhecidos ou valores não booleanos tornam a configuração inválida.
- `contacts.update` altera um contato no contexto da conta inteira, mesmo com vínculo comprovado a uma inbox.
- HTTPS é exigido para destinos remotos por padrão; `http://localhost`, `127.0.0.0/8` e `::1` são permitidos; `allow_insecure_http: true` libera uma exceção deliberada para HTTP interno.
- JSON de API é retornado integralmente, exceto o filtro técnico de itens de inbox não solicitada. Tokens, cabeçalhos e exceções HTTP brutas não devem aparecer nos resultados ao modelo.

Consulte [Segurança do perfil](SEGURANCA_PERFIL.md) e [Homologação](HOMOLOGACAO.md).
