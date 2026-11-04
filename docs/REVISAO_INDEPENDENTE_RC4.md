# Solicitação de parecer independente — Hermes Chatwoot Plugin 0.2.0rc4

**Escopo:** revisão de código e contratos na branch `homolog`, sem autorização de implantação ou de escrita real.

## Referências

- Base defeituosa: `5c2710bfb551863e2213e4ec6cfd2c4d32a31e0b` (0.2.0rc3)
- Revisão submetida: **usar o HEAD imutável da `homolog` no momento da avaliação e registrar o SHA integral**
- SDK usado nos testes CI: `ital-leste/chatwoot-client@ef7254b5e45d27e710e23a4c6bc255f55d147206`
- Base técnica: `PARECER-TECNICO-v0.2.0rc3.md` e `REVISAO-INDEPENDENTE-PLANO-DE-CORRECAO.md` (pareceres externos; não necessariamente versionados aqui)

## Fronteira entre os envelopes

1. **Envelope do orquestrador para Hermes**: contexto mínimo de lote, IDs, mensagens e correlação. Construído pelo sistema consumidor, não pelo plugin genérico.
2. **JSON da API Chatwoot para plugin/Hermes**: dados nativos retornados pelo SDK. O plugin valida uma *visão interna* do recurso, mas devolve o JSON individual original em `data`.
3. **Pesquisas e históricos por inbox**: preservam formato e campos nativos dos itens permitidos; retiram apenas os candidatos fora da inbox. Metadados de contagem podem refletir os dados anteriores ao filtro.

O agente usa o lote para decisões simples sem leituras redundantes; pode consultar o Chatwoot via plugin quando precisar de contexto mais completo. O plugin não resume o JSON nativo em ID/conteúdo. O consumidor continua responsável pelo destino, autorização contextual, handoff, eventual publicação e reconciliação.

## Correções submetidas

| ID | Componente | Critério |
|---|---|---|
| F1 | `validators.py`, `operations/contacts.py` | Envelopes conhecidos reconhecidos; envelope individual preservado; desconhecidos/ambíguos rejeitados |
| F5 | Idem | Identificadores positivos *não booleanos*, conta e inbox consistentes, busca e histórico sem contradições |
| F2 | `service.py`, `operations/` | Validação tipada anterior ao método, resultado desconhecido após tentativa potencial ambígua, sem retry |
| F3 | `schemas.py` | Campos e tipos de `Contact` anunciados; objetos de atributos livres e validação Python independente |
| F4 | README e homologação | Instalação documentada por SHA completo informado em relatório/PR, sem autorreferência no README |
| F6 | CI, documentação | SDK real com SHA fixo nos testes; instalação no Python do Hermes ainda exige provisionamento de homologação |

## Matriz de revisão requerida ao Hermes

1. Confirmar **12 ferramentas** no diagnóstico nativo, imports e handlers no Hermes instalado.
2. Repetir as regressões F1/F5 com SDK real e `MockTransport`, incluindo envelope plano, `payload`, `payload.contact`, IDs inválidos, busca com detalhe divergente, histórico vazio e conta contraditória. Confirmar ausência de dados de outra inbox nas listas.
3. Repetir F2 com HTTP 200/201 inválido, 5xx, timeout, 4xx conhecidos, erro de serialização e erro na finalização do cliente; verificar métodos e quantidade de requisições. Etiquetas sem mudança e GET interno com falha não devem produzir POST.
4. Comparar schema original de `Contact`, schema adaptado pelo **Hermes e provedor efetivamente escolhido** e validação Python para nulabilidade/objetos livres. Não delegar a autorização ao schema.
5. Verificar ausência de segredos nos argumentos, erros, resultados e logs de responsabilidade do plugin.
6. Confirmar que a versão do SDK usada pelo agente é a revisão explicitamente homologada. Testes em outro venv não bastam.
7. Distinguir prova offline (Gate Código), prontidão de perfil (Gate Integração) e execução real Chatwoot (Gate Operacional).

## Critérios e limites

**Gate Código:** F1, F2, F3 e F5 corrigidos; testes originais e regressões com SDK real verdes; CI e registro nativo aprovados; F4 documentado.

**Gate Prontidão:** perfil de testes, secret scope, SDK e interpretador correto, versões e autorização de escopo definidos.

**Gate Integração:** invocação real pelo Hermes, leitura real, escrita somente quando especificamente autorizada; autoria e efeitos observados.

**Gate Distribuição:** artefato/licença/provisionamento reproduzível e compatibilidade declarada; avaliação de atendimento autônomo é separada.

Não promover automaticamente a `main`. Não declarar execução integrada com base apenas em `pytest` ou `doctor`. O parecer deve registrar PASS/FAIL/NÃO VERIFICADO, evidência e correção mínima, sem solicitar novas ferramentas ou reimplementar HTTP.
