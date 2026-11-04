# Arquitetura da v0.2.0rc4

## Objetivo

Uma instalação do plugin por perfil Hermes com **uma URL Chatwoot e múltiplas credenciais de usuários**, definidas e protegidas fora do modelo. Cada ferramenta informa explicitamente `account_id`, `inbox_id` e o ID do recurso quando aplicável. O plugin valida a consistência com a API, respeita permissões declaradas, executa chamadas por meio do `CWClient` e devolve o JSON nativo.

## Fluxo

```text
Hermes register(ctx)
  -> lê plugin.yaml e registra 12 schemas/handlers
  -> NÃO conecta ao Chatwoot no carregamento

Chamada (credential, account_id, inbox_id, conversation_id, dados):
  -> ToolService valida esquema e configurações do perfil
  -> verifica allowed_operations / writable_contact_fields
  -> escolhe somente uma identidade configurada em credentials e confere igualdade entre o `account_id` informado e o `account_id` único da credencial
  -> agent.secret_scope.get_secret(base_url_env)
  -> agent.secret_scope.get_secret(credentials[credential].token_env)
  -> valida HTTP(S) e instancia CWClient(base_url, token) com context manager
  -> consulta conversation / contact_inbox quando necessário
  -> rejeita recursos associados à inbox errada
  -> executa método público do chatwoot_client
  -> devolve JSON integral dos recursos autorizados
  -> encerra o CWClient
```

A conexão não possui aliases de instalações nem mudanças arbitrárias de servidor por sessão. `credential` é uma identidade autorizada por configuração que seleciona o token de um usuário dentro daquela instalação. A seleção explícita não prova autorização pelo usuário humano ou pelo contexto de atendimento. Outro perfil Hermes pode carregar o mesmo código e outra URL/coleção de tokens. Um consumidor mais complexo que alterna conexões por execução precisará de um provedor confiável apropriado ao seu runtime — **não** há seleção dinâmica de servidores por argumento de modelo na v0.2.

## Estrutura

| Módulo | Fronteira |
| --- | --- |
| `plugin.yaml` | Manifesto e esquemas de nomes de variáveis de conexão/identidades |
| `__init__.py` | `register(ctx)` sem efeitos HTTP |
| `schemas.py` | JSON Schemas das 12 ferramentas |
| `tools.py` | Adaptadores Hermes; não inferem destinatário por `session_id` |
| `config.py` | Configuração imutável, catálogo de identidades autorizadas, vínculo de uma única conta por credencial e permissões |
| `connection.py` | Leitura de URL/token do perfil, validação HTTP(S) e construção do cliente externo |
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
- Nenhum hook captura tokens de outro plugin, nenhum `.env` do plugin é lido. Todos os nomes de variáveis são definidos no perfil. `agent.secret_scope.get_secret` preserva o escopo do perfil quando suportado pelo Hermes; a instalação deve comprovar esse isolamento.
- O plugin não recebe nem retorna o valor do token ao agente. Um `credential` escolhido pelo modelo seleciona uma identidade permitida no perfil, não a própria autorização humana de usar aquela identidade. Escopo por sessão fica com o consumidor.
- Adição/remoção de etiquetas no cliente é leitura + escrita, não transacional. Não há retry automático de escrita.

## Contratos distintos: lote e API

O envelope de lote `EnvelopeHermes` pertence ao consumidor/orquestrador. Ele identifica mensagens, IDs e correlação, fornecendo contexto mínimo ao agente. O plugin **não recebe** esse envelope nem produz outro resumo obrigatório dos recursos consultados. A resposta de `CWClient` é mantida nativa em `data` após validações internas. Nas consultas de contato individual a visão extraída é somente interna; nas pesquisas/históricos a lista é limitada à inbox, sem reduzir campos dos itens retidos. O agente pode consultar a API por necessidade contextual, mas não deve ser forçado a repetir leituras suficientes no lote.

## Falhas depois de método potencialmente modificador

`outcome_unknown` sinaliza incerteza quanto ao efeito. O SDK pode ter realizado GET interno antes de escrever e inclusive não ter enviado POST. O plugin não afirma transmissão nem aplica retry. O consumidor de atendimento é responsável por idempotência, reconciliação e autoridade de publicação única.
