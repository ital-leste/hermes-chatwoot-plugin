# Changelog

## 0.1.0 — 2026-11-03

- Estrutura nativa de plugin Hermes (`plugin.yaml`, `register(ctx)` e schemas).
- Sete ferramentas sobre a interface pública de `ital-leste-chatwoot-client`.
- Configuração para múltiplas instalações nomeadas, com credenciais externas, contas, inboxes e allowlist explícita de operações (`true`/`false` ou comentário/ausência).
- Guarda de inbox por consulta real da conversa quando existe filtro.
- Retorno JSON textual padronizado, sem exposição de segredos ou retry automático de escrita.
- Testes simulados, documentação de arquitetura, configuração, ferramentas e homologação.
- Distribuição automática do cliente e homologação real Hermes/Chatwoot pendentes.
