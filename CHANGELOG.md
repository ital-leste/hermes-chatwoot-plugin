# Histórico

## 0.2.0rc2 — homolog

- Elimina `installation`/aliases e define uma conexão Chatwoot por perfil Hermes.
- Introduz `config_schema.api_token` como segredo `CHATWOOT_API_TOKEN` e mantém URL em configuração do perfil.
- Exige `account_id`, `inbox_id` e `conversation_id` nas sete operações vinculadas a conversas, com conferência obrigatória antes da operação.
- Adiciona descoberta/listagem de conversas, busca/consulta de contatos, consulta de conversas do contato e edição restrita por campos: 12 ferramentas.
- Implementa HTTPS obrigatório fora de loopback, com exceção HTTP explícita.
- Mantém JSON nativo integral, exceto exclusão técnica de recursos fora da inbox solicitada em pesquisas.
- Separa operações por domínio e testa permissões, isolamento de conexão e erros.
- **Pendente:** publicação/licença da biblioteca Python e homologação real Hermes/Chatwoot.

## 0.1.0 — main inicial

- Sete ferramentas com instalações nomeadas e permissões por instalação.
