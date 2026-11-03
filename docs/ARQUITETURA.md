# Arquitetura — Hermes Chatwoot Plugin v0.1

## Objetivo

Prover ferramentas nativas de agente Hermes para a Application API do Chatwoot. O plugin **não** é um pipeline de atendimento, nem um client HTTP alternativo. Toda operação de rede Chatwoot passa pelo pacote externo `chatwoot_client`.

## Fluxo

```text
Hermes Tool Call (installation, account_id, conversation_id, argumentos)
  -> handler_for() / ToolService.execute()
  -> validação estrita de argumentos
  -> ctx.get_config("installations") / parse_installations()
  -> autorização por operação e conta
  -> agent.secret_scope.get_secret(token_env)
  -> CWClient(base_url, token)
  -> consulta de guarda da inbox (se filtrada)
  -> chamada pública da biblioteca Python
  -> resultado JSON nativo dentro do envelope da ferramenta
```

A URL e o token são selecionados **exclusivamente** pelo alias de configuração. Não há capacidade no catálogo para alterar a configuração ou passar token/URL em ferramenta. Uma instância `CWClient` é aberta e fechada por execução, evitando vazamento de contexto entre instalações e threads. O operador pode ter uma ou N instalações, inclusive diferentes contas e políticas.

## Fronteiras dos módulos

| Módulo | Responsabilidade |
| --- | --- |
| `plugin.yaml` | Manifesto e `config_schema` nativo |
| `__init__.py` | Registrar ferramentas com `ctx.register_tool(...)` |
| `schemas.py` | JSON Schema visível para o LLM |
| `tools.py` | Adapter de handler Hermes com `**kwargs` de contexto |
| `chatwoot_tools/config.py` | Contrato imutável e validação estrita de instalações |
| `chatwoot_tools/permissions.py` | Autorizar operação, conta e conferir associação da conversa à inbox |
| `chatwoot_tools/client_factory.py` | Instanciar `CWClient` e resolver token na API do Hermes |
| `chatwoot_tools/service.py` | Orquestrar uma chamada e mapear erros para JSON textual |
| `chatwoot_tools/errors.py` | Códigos próprios do plugin |

Nenhum módulo importa código de `chawoot-hermes-agent`, Evolution API, SQLite ou repositórios externos do produto.

## Regras funcionais

- Ferramentas registradas **não** significam autorização. O catálogo fica estável; a permissão é conferida para cada execução e instalação.
- O nome da operação, não o nome do método Python, é a chave de autorização: `messages.send_public`, etc.
- Configurações ausentes/erradas ou operações desconhecidas falham fechadas. O plugin rejeita propriedades extras fornecidas pelo modelo.
- Configuração de contas é obrigatória; `allowed_inbox_ids` é opcional. Quando existe, o plugin valida a identidade da conversa e a inbox retornada pela API antes de ler/escrever outros recursos. Essa checagem é uma política estática de escopo, **não** uma prova de destinatário pretendido pelo consumidor.
- A leitura interna de guarda é permitida mesmo sem `conversation.read` se necessária para implementar uma permissão de escrita restrita por inbox; não retorna esses dados ao agente.
- Respostas mantêm o corpo JSON nativo em `data`, sem truncar ou normalizar os campos da API. O plugin **não** garante entrega externa nem sucesso de efeitos por apenas receber HTTP 2xx.
- Etiquetas `add/remove` dependem de leitura seguida de escrita no cliente, sem atomicidade: consumidores precisam ordenar concorrência quando relevante.
- Não há retry automático: uma falha de transporte em escrita pode significar resultado desconhecido. O consumidor deve reconciliar antes de repetir.

## Limitações deliberadas

O plugin não implementa autorização por sessão, titularidade de conversa, handoff, detecção de duplicidade entre runs, dedupe de mensagens, rastreamento de efeitos, ACL de pessoas ou autorização externa. Esses controles pertencem ao consumidor do plugin.

O catálogo v0.1 contém **sete ferramentas**. Contatos (leitura/criação/atualização), `writable_contact_fields`, mídias e operações administrativas são reservados para ciclos posteriores; não há permissões implícitas para tais endpoints.

## Distribuição

O Hermes oferece dependências Python gerenciadas, mas não admite requisitos por URL Git direta em seu gerenciador. Como a biblioteca cliente ainda não está num índice gerenciado, a v0.1 requer instalação explícita do cliente no runtime Hermes. A release distribuível exige um índice versionado acessível. Esse limite deve ser documentado, não contornado por cópia de código ou import clandestino.
