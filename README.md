# Hermes Chatwoot Plugin

Plugin nativo para o Hermes Agent que transforma operações públicas da biblioteca Python [`chatwoot_client`](https://github.com/ital-leste/chatwoot-client) em ferramentas de leitura e escrita na Application API do Chatwoot.

**Estado:** `0.2.0rc1` em homologação; testes locais e CI simulados, **sem homologação real em um Hermes/Chatwoot operacional**. Esta versão altera o contrato de ferramentas da v0.1 (incompatível com chamadas antigas que usavam `installation`).

## Arquitetura e identidade

- Uma **conexão por perfil Hermes**: `base_url` na configuração; o token no cofre/ambiente seguro do perfil, resolvido pelo Hermes como `CHATWOOT_API_TOKEN`.
- **Sem aliases, sem catálogo de instalações, sem `.env` próprio do plugin** e sem token/URL nos parâmetros de ferramentas. Perfis distintos podem usar conexões distintas.
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
        base_url: "https://chatwoot.exemplo.com"
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

O manifesto declara `api_token` como `type: secret` associado a `CHATWOOT_API_TOKEN`. Configure o segredo pelo gerenciador de credenciais do perfil Hermes (ou ambiente protegido fornecido ao respectivo processo). **Não coloque o token no YAML, no repositório ou em uma ferramenta.** O carregamento real do segredo e o isolamento entre perfis dependem da instalação Hermes e precisam ser testados no alvo.

Remover/comentar uma permissão é equivalente a `false`. Operações não declaradas são negadas. Atualizações de contato negam o payload inteiro quando inclui qualquer campo não autorizado.

HTTPS é obrigatório fora de loopback, salvo `allow_insecure_http: true` definido pelo operador em rede interna controlada. O nome de uma máquina em VPN não é automaticamente considerado loopback.

## Ferramentas (12)

| Ferramenta | Operação autorizadora | IDs obrigatórios |
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
{"account_id": 1, "inbox_id": 4, "conversation_id": 482, "content": "Bom dia!"}
```

O plugin confere a associação com `conversations.get()` e só então chama `messages.send_text()` do cliente. Não garante entrega no WhatsApp após HTTP 2xx. Falhas após início da escrita podem ter resultado indeterminado, e não devem ser repetidas cegamente.

Veja [Ferramentas](docs/FERRAMENTAS.md), [Configuração](docs/CONFIGURACAO.md) e [Arquitetura](docs/ARQUITETURA.md).

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
- [Histórico de versões](CHANGELOG.md)
