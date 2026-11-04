# Solicitação de parecer independente — Hermes Chatwoot Plugin rc4

**Branch:** `homolog`  
**Base anterior:** `5c2710bfb551863e2213e4ec6cfd2c4d32a31e0b`  
**Candidato:** HEAD imutável da `homolog` no momento da revisão; registrar o SHA final no relatório e no PR. Não inserir SHA autorreferente neste documento.

## Objetivo
Avaliar a implementação sem pressupor aprovação por testes simulados ou pelo desenho arquitetural. Não instalar nem executar operações reais no Chatwoot sem autorização específica. Não promover a `main`.

## Contrato arquitetural
O orquestrador entrega ao Hermes um lote mínimo e rastreável, com tríade e IDs de mensagens. O plugin não substitui esse envelope e não projeta os recursos nativos da API em representações reduzidas. Consulta individual: manter o JSON original em `data`. Busca e histórico por inbox: filtrar apenas recursos fora de escopo e preservar os campos nativos dos itens restantes e metadados da API, explicitando que contagens podem anteceder o filtro.

## Revisar
1. F1: `contact_view` e `_check_contact` reconhecem envelopes conhecidos, rejeitam ambiguidades e validam identificadores com tipo exato? Há formatos reais do SDK não contemplados?
2. F5: associação com inbox e conta em contatos, histórico e busca; divergência entre candidato e detalhe; página filtrada vazia; histórico vazio; paginação; falsos positivos/negativos.
3. F2: falhas após método potencialmente modificador são `outcome_unknown` conservador, incluindo status HTTP, JSON e fechamento. Etiquetas podem executar GET antes de POST ou nenhum POST; não alegar transmissão comprovada. Verificar se falhas de preparação são classificadas corretamente e se há exceções não capturadas.
4. F3: campos/tipos de `Contact` versus schema e validação Python; `null`, `false`, `{}`, atributos aninhados, não finitos, omissão, tipos inválidos. Verificar transformação pelo sanitizador Hermes e pelo provedor/modelo.
5. F4/F6: dependência externa ainda não publicada/instalada automaticamente; documentação de provisionamento por revisão fixa no Python do processo Hermes; licença e distribuição estável ainda pendentes.
6. Validar chamadas HTTP simuladas com SDK real, método, quantidade e ordem; confirmar ausência de POST em no-op de etiquetas e classificação da falha em GET interno.
7. Validar isolamento do perfil, múltiplos tokens na mesma instalação, credencial vinculada a uma única conta, segredo resolvido pelo Hermes e registro das 12 ferramentas.

## Gates
- **Código corrigido:** regressões, SDK real com transporte simulado, CI, docs e registro nativo.
- **Pronto para integração:** ambiente Python do processo, perfil, credenciais e permissões.
- **Homologação operacional:** chamadas reais controladas e autoria/efeitos confirmados.
- **Distribuição estável:** licença, dependência versionada e release; atendimento autônomo tem gate próprio.

## Entrega solicitada ao revisor
Parecer técnico com evidências e linhas, classificação de cada frente (aprovada/parcial/reprovada), reprodução de falhas, regressões faltantes, risco residual e recomendação explícita de manter `homolog`, corrigir novamente ou prosseguir ao próximo gate. A aprovação do código não implica autorização de implantação.
