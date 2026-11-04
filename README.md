# Hermes Chatwoot Plugin

Plugin nativo para o Hermes Agent que transforma operações públicas da biblioteca Python [`chatwoot_client`](https://github.com/ital-leste/chatwoot-client) em ferramentas de leitura e escrita na Application API do Chatwoot.

**Estado:** `0.2.0rc2` em homologação; testes locais e CI simulados, **sem homologação real em um Hermes/Chatwoot operacional**. Esta versão altera o contrato de ferramentas da v0.1 (incompatível com chamadas antigas que usavam `installation`).

## Arquitetura e identidade

- **Uma instalação Chatwoot por perfil Hermes**: `base_url_env` aponta para a URL no `.env` do perfil; `credentials` relaciona as identidades de usuários autorizados aos nomes das variáveis de token, também do perfil.
- **Vários tokens na mesma instalação e conta** são permitidos (ex.: `italbot`, `luiz`, `marcio`); cada ferramenta exige `credential`, que escolhe uma identidade explicitamente autorizada na configuração, não o valor do token.
- **Sem aliases de instalações, sem `.env` do plugin** e sem valores de token/URL nos argumentos de ferramenta. Perfis distintos podem usar URLs e tokens diferentes.
- Operações de conversa exigem `account_id`, `inbox_id`, `conversation_id`. O plugin consulta o Chatwoot e comprova a associação antes de ler ou escrever.
- Pesquisas de conversas exigem `account_id` e `inbox_id`; pesquisas de contatos usam essa dupla, e operações sobre contatos exigem `contact_id` adicional.
- Uma tríade válida não prova que o modelo escolheu a conversa pretendida pelo evento do consumidor. A autorização por sessão, idempotência, handoff e políticas de atendimento continuam fora do plugin.
- Respostas de recursos são JSON nativo integral. Nas **pesquisas por inbox**, itens de outra inbox são excluídos para respeitar a restrição de destino; seus campos originais não são projetados ou ocultados.
- O plugin não abre servidor, não persiste dados, não importa Evolution API e não executa HTTP Chatwoot sem `chatwoot_client`.

## Configuração do perfil

No `config.yaml` do perfil Hermes que executa o plugin:

```yaml
plugins:
  enabled:
    - chatwoot-tools
  entries:
    chatwoot-tools:
      settings:
        base_url_env: CHATWOOT_BASE_URL
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
        allow_insecure_http: false
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

O operador cadastra os valores no `.env` do perfil (ex.: `~/.hermes/profiles/italbot/.env`):

```dotenv
CHATWOOT_BASE_URL=https://chatwoot.exemplo.com
CHATWOOT_ITALBOT_TOKEN=<token_italbot>
CHATWOOT_LUIZ_TOKEN=<token_luiz>
CHATWOOT_MARCIO_TOKEN=<token_marcio>
```

Os valores entre `<...>` são apenas exemplos e devem ser substituídos. O plugin chama `agent.secret_scope.get_secret(nome)` para ler a URL e o token no escopo do perfil. **Não armazene tokens no YAML, no Git ou nos argumentos das ferramentas.** A configuração do perfil e o mecanismo de segredos do Hermes são a fonte de autoridade; não há arquivo `.env` no repositório do plugin. Após editar arquivos do perfil, confirme se a versão do Hermes exige reinício/reload da sessão para aplicar as alterações.

Adicionar uma identidade requer incluir uma entrada em `credentials` e a variável correspondente no `.env` do perfil; remover a entrada revoga imediatamente a seleção daquela identidade assim que a configuração atualizada for carregada. Rotacionar um token não exige alterar o código. A lista `allowed_account_ids` define em quais contas cada credencial pode ser utilizada.

Remover/comentar uma permissão é equivalente a `false`. Operações não declaradas são negadas. Atualizações de contato negam o payload inteiro quando inclui qualquer campo não autorizado.

HTTPS é obrigatório fora de loopback, salvo `allow_insecure_http: true` definido pelo operador em rede interna controlada. O nome de uma máquina em VPN não é automaticamente considerado loopback.

## Ferramentas (12)

| Ferramenta | Operação autorizadora | IDs obrigatórios (além de `credential`) |
| --- | --- | --- |
| `chatwoot_get_conversation` | `conversation.read` | account, inbox, conversation |
| `chatwoot_list_conversations` | `conversation.list` | account, inbox |
| `chatwoot_list_messages` | `messages.read` | account, inbox, conversation |
| `chatwoot_send_public_message` | `messages.send_public` | account, inbox, conversation |
| `chatwoot_send_private_note` | `messages.send_private` | account, inbox, conversation |
| `chatwoot_set_status` | `conversation.status.update` | account, inbox, conversation |
| `chatwoot_add_labels` | `conversation.labels.add` | account, inbox, conversation |
| `chatwoot_remove_labels` | `conversation.labels.remove` | account, inbox, conversation |
| `chatwoot_search_contacts` | `contacts.search` | account, inbox |
| `chatwoot_get_contact` | `contacts.read` | account, inbox, contact |
| `chatwoot_get_contact_conversations` | `contacts.conversations.read` | account, inbox, contact |
| `chatwoot_update_contact` | `contacts.update` | account, inbox, contact |

Exemplo de publicação:

```json
{"credential": "italbot", "account_id": 1, "inbox_id": 4, "conversation_id": 482, "content": "Bom dia!"}
```

O plugin resolve `credential` no mapa autorizado, confere a conta permitida, recupera o token pelo nome da variável e então confere a associação com `conversations.get()` e só então chama `messages.send_text()` do cliente. Não garante entrega no WhatsApp após HTTP 2xx. Falhas após início da escrita podem ter resultado indeterminado, e não devem ser repetidas cegamente.

Veja [Ferramentas](docs/FERRAMENTAS.md), [Configuração](docs/CONFIGURACAO.md) e [Arquitetura](docs/ARQUITETURA.md).

## Limites da escolha de usuário

`credential` é uma **identidade de autenticação configurada**, não uma prova de que a pessoa correspondente solicitou a operação. Um agente que possua as credenciais `luiz` e `marcio` habilitadas poderá selecionar qualquer uma delas. Para exigir que determinado atendimento utilize apenas uma identidade, restrinja as entradas de `credentials` disponibilizadas ao perfil ou vincule a identidade por um consumidor confiável; a v0.2rc2 ainda não realiza autorização por sessão.

O Chatwoot determina a atribuição do autor com base no token e nas próprias permissões da conta. Essa atribuição precisa ser verificada na homologação real, inclusive para mensagens públicas e notas privadas. Usar o nome `luiz` na ferramenta **não** altera a autoria por si só.

Veja [Segurança do perfil](docs/SEGURANCA_PERFIL.md) para as configurações de execução de comandos e proteção dos segredos.

## Instalação e limitação de distribuição

```bash
hermes plugins install ital-leste/hermes-chatwoot-plugin
hermes plugins enable chatwoot-tools
hermes plugins list
hermes plugins validate .
hermes plugins doctor . --ci
```

**Bloqueio de distribuição ainda aberto:** `ital-leste-chatwoot-client` não foi confirmado como publicado num índice Python gerenciável pelo Hermes, e sua licença de distribuição ainda precisa ser decidida pelo titular. Até concluir essas duas etapas, o plugin mantém `dependencies = []`, e a biblioteca precisa ser instalada **separadamente no Python efetivo do Hermes**, por exemplo para homologação controlada:

```bash
python -m pip install "git+https://github.com/ital-leste/chatwoot-client.git@ef7254b5e45d27e710e23a4c6bc255f55d147206"
python -c "from chatwoot_client import CWClient; print('OK')"
```

Esse procedimento é provisório. Não se deve instalar o cliente homônimo `chatwoot-client` de outro mantenedor no PyPI: ele **não** corresponde a `ital-leste-chatwoot-client`. A dependência formal só será adicionada após publicação verificável da distribuição correta em índice autorizado. Não copie o código da biblioteca para o plugin.

## Testes e homologação

```bash
python -m pip install 'pytest>=8,<10' 'PyYAML>=6,<7'
python -m pytest -q
```

Os testes usam doubles de `CWClient` e não comprovam integração real. A validação integrada deve ser feita com credenciais de teste e autorização explícita, iniciando por permissões somente de leitura. Ver [Plano de homologação](docs/HOMOLOGACAO.md).

## Documentação

- [Arquitetura](docs/ARQUITETURA.md)
- [Configuração e segurança](docs/CONFIGURACAO.md)
- [Contratos das ferramentas](docs/FERRAMENTAS.md)
- [Homologação](docs/HOMOLOGACAO.md)
- [Segurança do perfil Hermes](docs/SEGURANCA_PERFIL.md)
- [Histórico de versões](CHANGELOG.md)
