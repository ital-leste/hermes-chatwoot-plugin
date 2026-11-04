# Segurança do perfil Hermes para atendimento

Este documento descreve **critérios de implantação**, não capacidades de sandbox implementadas pelo plugin Chatwoot. Um perfil separado possui configurações/memória/segredos próprios, mas não prova sozinho que o agente está impedido de ler arquivos ou executar comandos.

## Princípios

1. Permitir no Hermes somente as ferramentas de atendimento realmente necessárias. Desabilitar acesso ao terminal, execução de código, shells, escrita/leitura indiscriminada de arquivos, modificação de configurações e ferramentas administrativas, quando não forem necessárias ao atendimento.
2. Confirmar na versão real do Hermes que o bloqueio de ferramentas é efetivo. Não confiar apenas em instruções do prompt ou arquivos `SOUL.md`.
3. Manter URL e tokens Chatwoot no `.env`/escopo de segredos do perfil, não no contexto do modelo, em tool calls, repositórios ou logs.
4. Considerar isolamento de sistema operacional, usuário de serviço, contêiner e/ou `plugins.isolation: host` (conforme suporte da versão instalada). A escolha de ferramentas deve ser restrita no host além de na configuração do perfil para aplicações de alto risco.
5. Evitar expor múltiplos tokens humanos a um agente autônomo quando o fluxo permitir escolher uma identidade arbitrária. As credenciais em `credentials` são um conjunto permitido; a v0.2rc2 **não** comprova que Operador A autorizou determinado envio. Se a autoria for determinada por handoff, o consumidor deve associar uma identidade autenticada à execução por canal confiável ou usar um perfil restrito àquela identidade.
6. Restringir cada identidade a um único `account_id` e `allowed_operations` globalmente. Revisar os tokens e permissões reais no Chatwoot; o plugin não amplia privilégios do token.
7. Alterar um token no `.env` exige confirmar o refresh/reload no runtime Hermes. Remover do YAML impede novas chamadas daquela identidade quando a configuração for carregada, mas não revoga o token no servidor: revogue-o também no Chatwoot quando necessário.

## Testes de aceite no Hermes/VPS

- Com `atendimento` habilitado, pedir execução de comando e leitura de `config.yaml`/`.env`: nenhum recurso de terminal ou leitura arbitrária deve estar acessível.
- Chamar ferramenta com `credential` inexistente: rejeição antes da rede.
- Chamar ferramenta usando uma identidade válida, mas conta divergente do único `account_id` configurado: rejeição antes da rede.
- Chamar ferramenta com IDs de inbox/conversa divergentes: rejeição antes da escrita.
- Fazer atendimento de teste com tokens de Operador A e Operador B e verificar atribuição de autoria no Chatwoot, distinguindo mensagem criada de entrega ao canal externo.
- Atualizar e remover credencial configurada; verificar propagação efetiva das alterações sem reinicialização inesperada e sem credenciais expostas.
- Em gateways multiplexados, executar testes cruzados entre perfis, garantindo que `agent.secret_scope.get_secret` não leia valores de outro perfil.

O plugin não implementa políticas de handoff, bloqueio de terminal, controle de sessão ou ACL de operador. Esses mecanismos pertencem à configuração e ao ambiente de execução do Hermes e ao consumidor.

Referências: https://hermes-agent.nousresearch.com/docs/user-guide/profiles ; https://hermes-agent.nousresearch.com/docs/developer-guide/plugins ; https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins
