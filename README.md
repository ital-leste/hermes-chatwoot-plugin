# Hermes Chatwoot Plugin

Plugin **nativo do Hermes Agent** que disponibiliza sete ferramentas para consultar conversas, ler mensagens, publicar textos/notas privadas, alterar status e gerenciar etiquetas no Chatwoot. Todas as chamadas à Application API são executadas pela biblioteca Python independente [`ital-leste/chatwoot-client`](https://github.com/ital-leste/chatwoot-client).

**Estado:** v0.1.0 inicial, testes simulados. **Não há homologação real Hermes ↔ Chatwoot nem publicação em produção** nesta revisão. A API do cliente foi modelada com base no Chatwoot 4.19.0; a compatibilidade com outras versões depende de validação integrada.

## Limites e arquitetura

- Uma ou várias instalações Chatwoot, identificadas pelo parâmetro obrigatório `installation` em todas as ferramentas.
- Cada instalação possui `base_url`, `token_env`, contas autorizadas, restrição opcional de inboxes e operações declaradas com `true`.
- **Por padrão, todas as operações são negadas.** Comentar/remover uma linha ou atribuir `false` a uma permissão bloqueia sua execução. Nomes desconhecidos falham na validação da configuração.
- O Chatwoot autentica o token e valida o acesso aos recursos; o plugin verifica adicionalmente as permissões configuradas pelo operador.
- Quando `allowed_inbox_ids` está configurado, o plugin consulta a conversa e verifica a inbox **antes da operação**, inclusive antes de escritas. Sem a restrição, não realiza essa leitura de guarda automaticamente (exceto na própria consulta da conversa).
- O plugin **não decide** o destinatário pretendido por determinado fluxo de atendimento. Essa decisão e políticas de sessão, handoff, idempotência e auditoria são do consumidor.
- Não há persistência, daemon, servidor HTTP próprio, comandos Evolution, acesso ao banco de dados Chatwoot, retry de escrita ou dependência do `chawoot-hermes-agent`.

## Ferramentas

| Ferramenta | Permissão YAML | Efeito |
| --- | --- | --- |
| `chatwoot_get_conversation` | `conversation.read` | Consultar uma conversa |
| `chatwoot_list_messages` | `messages.read` | Listar mensagens (cursores opcionais) |
| `chatwoot_send_public_message` | `messages.send_public` | Publicar texto público |
| `chatwoot_send_private_note` | `messages.send_private` | Publicar nota privada |
| `chatwoot_set_status` | `conversation.status.update` | Alterar estado `open/pending/resolved/snoozed` |
| `chatwoot_add_labels` | `conversation.labels.add` | Acrescentar etiquetas |
| `chatwoot_remove_labels` | `conversation.labels.remove` | Remover etiquetas selecionadas |

Todas recebem `installation`, `account_id` e `conversation_id`; os campos específicos são descritos em [Ferramentas](docs/FERRAMENTAS.md).

## Configuração

No arquivo `~/.hermes/config.yaml`, configurar a entrada:

```yaml
plugins:
  enabled:
    - chatwoot-tools
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

          homolog:
            base_url: "http://127.0.0.1:3000"
            token_env: "HERMES_CHATWOOT_HOMOLOG_TOKEN"
            allowed_account_ids: [1]
            allowed_operations:
              conversation.read: true
              messages.read: true
              # messages.send_public: true
              # messages.send_private: true
              # conversation.status.update: true
              # conversation.labels.add: true
              # conversation.labels.remove: true
```

Disponibilize os tokens **no ambiente/gerenciador de segredos do Hermes**, com os nomes declarados em `token_env`. O plugin os resolve pela API `agent.secret_scope.get_secret`; **não** lê um `.env` próprio nem aceita tokens nos argumentos das ferramentas. Nunca versionar credenciais no Git.

`allowed_account_ids` é obrigatório, com ao menos um identificador. `allowed_inbox_ids` ausente significa que não há filtro adicional por inbox; uma lista vazia bloqueia todas as conversas. Quando definido, vale para leituras e escritas. Comentar/remover uma operação equivale a `false`. Leia [Configuração e permissões](docs/CONFIGURACAO.md).

## Instalação e dependência externa

O diretório raiz já está no formato nativo do Hermes (`plugin.yaml` + `__init__.py`). Após a publicação do repositório:

```bash
hermes plugins install ital-leste/hermes-chatwoot-plugin
hermes plugins list
hermes plugins enable chatwoot-tools
# Em checkout do repositório ou dentro da pasta instalada:
hermes plugins validate .
hermes plugins doctor . --ci
```

**Limitação de distribuição na v0.1:** o cliente `ital-leste-chatwoot-client` ainda não está publicado em um índice Python utilizado pelo gerenciador do Hermes. O manifesto do plugin, portanto, **não declara uma dependência impossível de resolver**. O operador deve garantir a presença de `chatwoot_client` **no mesmo runtime Python que executa o Hermes**, por exemplo, com o instalador desse ambiente:

```bash
python -m pip install "git+https://github.com/ital-leste/chatwoot-client.git@39891b8f6ce4f59911912d01a26a688202940cd8"
python -c "from chatwoot_client import CWClient; print('CWClient disponível')"
```

**Atenção:** o `python` dos comandos acima deve ser o interpretador gerenciado/usado pelo Hermes, não necessariamente o Python global da VPS. Atualizações do ambiente gerenciado podem substituir essa instalação manual. A distribuição plenamente automática depende de publicar a biblioteca versionada em um índice acessível ao Hermes. Esse é um critério pendente para a release distribuível. Em nenhum caso copie os módulos do cliente para este repositório.

Em ambientes mais antigos do Hermes, confirme o suporte a `config_schema` e `get_secret` antes de ativar o plugin. Consulte [Homologação](docs/HOMOLOGACAO.md).

## Exemplo de chamada

Ferramenta `chatwoot_send_public_message`:

```json
{
  "installation": "principal",
  "account_id": 17,
  "conversation_id": 482,
  "content": "Olá! Como podemos ajudar?"
}
```

A resposta é uma string JSON com `success`, `installation`, `operation` e `data` (JSON **nativo** do Chatwoot):

```json
{"success": true, "installation": "principal", "operation": "messages.send_public", "data": {"id": 7812}}
```

O retorno acima é ilustrativo: o plugin não inventa campos nem garante entrega no WhatsApp após HTTP 2xx. Em falhas há `success: false` e `error.code`, sem expor o conteúdo de exceções potencialmente sensíveis.

## Desenvolvimento

Python >=3.11, `pytest` e `PyYAML` somente para os testes:

```bash
python -m pip install "pytest>=8,<10" "PyYAML>=6,<7"
python -m pytest -q
```

A suíte usa doubles do cliente e do contexto Hermes; não depende de token, VPS ou Chatwoot real. É incorreto tratar essa regressão como homologação ponta a ponta.

## Documentos

- [Arquitetura](docs/ARQUITETURA.md) — componentes e limites.
- [Configuração e permissões](docs/CONFIGURACAO.md) — regras de segurança e política de negação.
- [Ferramentas](docs/FERRAMENTAS.md) — catálogo e contratos.
- [Homologação](docs/HOMOLOGACAO.md) — critérios de aceite e execução integrada.
- [Changelog](CHANGELOG.md) — histórico.

### Documentação de referência

- [Hermes — criação de plugins nativos](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/plugins/index.md)
- [Chatwoot Client — arquitetura e exemplos](https://github.com/ital-leste/chatwoot-client)
