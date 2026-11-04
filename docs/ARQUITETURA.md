# Arquitetura da v0.2.0rc1

## Objetivo

Uma instalação do plugin por perfil Hermes com conexão Chatwoot definida e protegida **fora do modelo**. Cada ferramenta informa explicitamente `account_id`, `inbox_id` e o ID do recurso quando aplicável. O plugin valida a consistência com a API, respeita permissões declaradas, executa chamadas por meio do `CWClient` e devolve o JSON nativo.

## Fluxo

```text
Hermes register(ctx)
  -> lê plugin.yaml e registra 12 schemas/handlers
  -> NÃO conecta ao Chatwoot no carregamento

Chamada (account_id, inbox_id, conversation_id, dados):
  -> ToolService valida esquema e configurações do perfil
  -> verifica allowed_operations / writable_contact_fields
  -> agent.secret_scope.get_secret("CHATWOOT_API_TOKEN")
  -> instancia CWClient(base_url, token) com context manager
  -> consulta conversation / contact_inbox quando necessário
  -> rejeita recursos associados à inbox errada
  -> executa método público do chatwoot_client
  -> devolve JSON integral dos recursos autorizados
  -> encerra o CWClient
```

A conexão não possui aliases nem mudanças por sessão. Outro perfil Hermes pode carregar o mesmo código e outra URL/token. Um consumidor mais complexo que alterna conexões por execução precisará de um provedor confiável apropriado ao seu runtime — **não** há seleção dinâmica de servidores por argumento de modelo na v0.2.

## Estrutura

| Módulo | Fronteira |
| --- | --- |
| `plugin.yaml` | Manifesto e esquema de configuração Hermes, incluindo segredo |
| `__init__.py` | `register(ctx)` sem efeitos HTTP |
| `schemas.py` | JSON Schemas das 12 ferramentas |
| `tools.py` | Adaptadores Hermes; não inferem destinatário por `session_id` |
| `config.py` | Configuração imutável e validação HTTP(S), operações/campos |
| `connection.py` | Token protegido e construção do cliente externo |
| `validators.py` | Validação de tríade e vínculo de contatos com inbox |
| `permissions.py` | Allowlist por operação e campo |
| `service.py` | Orquestração, lifecycle e erros estáveis |
| `operations/` | Chamadas públicas da biblioteca por domínio |

## Consistência e limites

- `account_id + inbox_id + conversation_id` designa conversa em um servidor determinado. O plugin confere a inbox por leitura da conversa retornada; a API impõe conta pelo caminho e, se houver `account_id` no objeto, o plugin também o compara.
- `account_id + inbox_id + contact_id` identifica o contato da conta com vínculo comprovável com a inbox; **não** identifica necessariamente uma conversa única.
- `contacts.search` é um endpoint por conta. Seus candidatos são conferidos por `contact_inboxes` ou histórico de conversas; somente candidatos da inbox solicitada são retornados. Isso altera o conjunto da busca, **não** os campos de cada contato.
- `contacts.update` modifica o cadastro do contato na conta inteira, inclusive para outras inboxes. A validação da inbox apenas comprova o vínculo de origem.
- Busca de contatos sem vínculo comprovável pode omitir candidatos legítimos ainda sem histórico/documentação de associação; falha fechada é preferível a exibir recursos de outra inbox.
- Se um endpoint alterar seu envelope, o plugin falha fechado em vez de inventar identidade. Os retornos precisam ser homologados com o Chatwoot 4.19.0 do consumidor.
- A tríade pode ser válida e ainda assim diferente da conversa que originou o evento; sessão, destinatário pretendido, deduplicação, handoff e retry ficam a cargo do consumidor.
- Nenhum hook captura tokens de outro plugin, nenhum `.env` do plugin é lido. Perfil mal isolado do Hermes pode compartilhar variáveis do SO; esse isolamento deve ser verificado.
- Adição/remoção de etiquetas no cliente é leitura + escrita, não transacional. Não há retry automático de escrita.
