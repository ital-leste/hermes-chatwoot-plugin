# Configuração e credenciais por perfil — v0.2.0rc4

O plugin utiliza um único servidor Chatwoot por perfil Hermes, mas pode autenticar vários usuários diferentes na mesma instalação, inclusive na mesma conta. As credenciais são gerenciadas pelo perfil, nunca por um arquivo do plugin.

## Arquivo `.env` do perfil Hermes

Exemplo em `~/.hermes/profiles/atendimento/.env` (o caminho real deve ser confirmado na instalação Hermes):

```dotenv
CHATWOOT_BASE_URL=https://chatwoot.exemplo.com
CHATWOOT_ATENDIMENTO_TOKEN=valor_atendimento
CHATWOOT_OPERADOR_A_TOKEN=valor_operador_a
CHATWOOT_OPERADOR_B_TOKEN=valor_operador_b
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
          atendimento:
            token_env: CHATWOOT_ATENDIMENTO_TOKEN
            account_id: 7
          operador_a:
            token_env: CHATWOOT_OPERADOR_A_TOKEN
            account_id: 7
          operador_b:
            token_env: CHATWOOT_OPERADOR_B_TOKEN
            account_id: 7
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

`base_url_env` contém o **nome** da variável com a URL. Cada identidade em `credentials` possui seu próprio `token_env` e um único `account_id` inteiro positivo. O campo `account_id` não aceita listas e a ferramenta deve informá-lo explicitamente; o plugin exige igualdade entre ambos. Nomes de variáveis devem ser válidos e distintos; não é permitido referenciar a mesma variável de token em duas identidades. Não há aliases de **instalações**, somente identificadores técnicos de **credenciais**. O identificador não precisa ser o nome real do usuário no Chatwoot e não confirma sua autoria: o servidor utiliza o token autenticado.

As doze ferramentas exigem `credential`, por exemplo `credential: "operador_a"`, além dos IDs de conta e inbox e, conforme a operação, do ID da conversa ou contato. O agente não fornece a URL, o nome da variável de ambiente ou o token. A seleção de uma identidade desconhecida ou não autorizada para a conta falha antes de qualquer chamada HTTP.

## Manutenção de usuários e tokens

- **Novo usuário:** cadastrar seu token no `.env` do perfil e incluir uma entrada em `credentials` com o `account_id` autorizado.
- **Rotação:** atualizar o valor da variável existente; nenhum arquivo de código do plugin precisa mudar.
- **Remoção:** excluir ou comentar a entrada do usuário em `credentials`. A tentativa de utilizar aquela identidade será rejeitada quando a configuração atualizada estiver ativa; revogar o token no Chatwoot se também for necessário impedir o uso por outros clientes.
- **Mudança de conta:** editar `account_id` daquela identidade; a API Chatwoot também deve autorizar o usuário na conta indicada.
- **Mudança de servidor:** configurar outro perfil Hermes/ambiente, com sua própria URL e tokens; não há escolha arbitrária de servidor nos argumentos das ferramentas.

A configuração e o valor da variável de ambiente devem estar carregados no runtime real. Em um gateway de perfil único, editar `.env` pode exigir reinicialização do processo; em multiplexação o escopo pode ser atualizado em outro momento. Não presumir rotação instantânea até verificar o procedimento do Hermes instalado.

## Segurança e operações

- O operador autoriza um conjunto de identidades no perfil. **O agente poderá escolher entre todas as identidades ali permitidas.** Essa seleção não é uma autorização específica de sessão ou de operador humano. Caso Operador A e Operador B não devam ser intercambiáveis em determinados atendimentos, separe os perfis ou implemente uma associação confiável de credencial por execução no consumidor.
- Todas as operações exigem `account_id` e `inbox_id`. Uma operação vinculada a conversa exige também `conversation_id`, conferindo a associação real antes de executar.
- `allowed_operations` e `writable_contact_fields` são mapas `nome: true`. Linhas ausentes/comentadas/`false` negam a operação/campo. Nomes desconhecidos ou valores não booleanos tornam a configuração inválida.
- `contacts.update` altera um contato no contexto da conta inteira, mesmo com vínculo comprovado a uma inbox.
- HTTPS é exigido para destinos remotos por padrão; `http://localhost`, `127.0.0.0/8` e `::1` são permitidos; `allow_insecure_http: true` libera uma exceção deliberada para HTTP interno.
- JSON de API é retornado integralmente, exceto o filtro técnico de itens de inbox não solicitada. Tokens, cabeçalhos e exceções HTTP brutas não devem aparecer nos resultados ao modelo.

Consulte [Segurança do perfil](SEGURANCA_PERFIL.md) e [Homologação](HOMOLOGACAO.md).

## Política de dados nativos

Não há redução automática de campos das respostas da Application API. Em operações individuais o JSON do SDK é devolvido tal como recebido em `data`. Em listagens limitadas à inbox os recursos de outras inboxes são excluídos; os campos e envelope dos itens permitidos são preservados. Credenciais de autenticação resolvidas pelo perfil não são inseridas nas respostas do plugin.
