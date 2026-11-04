# Histórico

## 0.2.0rc4 — homolog (correção F1–F5)

- Reconhece envelopes de contato para validação sem alterar o JSON original nas consultas individuais.
- Confere IDs, conta e inbox em contato, detalhe, busca e histórico; mantém filtro de recursos por inbox.
- Classifica conservadoramente tentativas de escrita ambíguas como `outcome_unknown`, inclusive etiquetas cujo SDK lê antes de eventualmente escrever.
- Alinha `fields` ao `Contact` tipado e mantém os mapas livres de atributos.
- Acrescenta regressões com SDK real e `httpx.MockTransport` em CI; provisionamento da dependência por SHA de homologação.
- Documenta instalação por SHA e separação dos gates de código, integração e release.
- Fecha divergência residual F3 para newline terminal em email/telefone, com testes SDK sem HTTP; documenta contexto correto de diagnóstico.
- CI também executa Python 3.14 e registra dependências de teste com versões fixadas.
- **Pendente:** validação real Hermes/Chatwoot, adaptação dos schemas no provedor alvo e distribuição formal do SDK.

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
