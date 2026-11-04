# Histórico

## 0.2.0rc3 — homolog

- Torna o plugin agnóstico: exemplos, testes e documentação não contêm dados ou nomes de uma organização consumidora.
- Substitui a lista `allowed_account_ids` por `account_id` único em cada identidade; nenhum token pode ser autorizado para várias contas por uma única entrada.
- Preserva a seleção explícita de credencial e de tríade nas ferramentas, com validação de igualdade antes de acessar a rede.
- Mantém dependência externa documentada sem acoplar o pacote à finalidade de uma empresa específica.

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
