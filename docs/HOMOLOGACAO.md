# Homologação Hermes Chatwoot Plugin — 0.2.0rc4

## Estado inicial

Versão candidata corretiva F1–F5. Os testes de contrato usam o SDK real com `httpx.MockTransport`; não há equivalência automática com execução no Chatwoot real. A biblioteca cliente externa ainda não tem distribuição automática aprovada no plugin.

## Gates independentes

1. **Código corrigido:** testes unitários e testes de contrato com SDK real, Python 3.11/3.12/3.13/3.14, métodos/rotas/contagem de HTTP simulados, manifesto e 12 handlers válidos, revisão por SHA e documentação coerente.
2. **Pronto para integração:** perfil Hermes de homologação, segredo e URL funcionais, SDK no *Python efetivamente utilizado pelo gateway/run*, permissões de leitura e escopo de testes definidos, reinício/rebuild com provisionamento documentado.
3. **Integração operacional:** `doctor`, ferramentas expostas e invocadas em run real; operações reais de leitura verificadas; escritas apenas após autorização específica, com autoria e reconciliação verificadas.
4. **Distribuição estável:** artefatos versionados, licença e dependência aprovadas, compatibilidade formalmente testada. Autonomia do atendimento e handoff pertencem ao consumidor.

## Testes de código

```bash
python -m pip install 'pytest==9.2.0' 'PyYAML==6.0.3' 'jsonschema==4.26.0'
python -m pip install 'git+https://github.com/ital-leste/chatwoot-client.git@ef7254b5e45d27e710e23a4c6bc255f55d147206'
python -m pip check
python -m pip freeze  # registrar no relatório técnico; não contém valores de segredos
python -m pytest -q -ra
python -m compileall -q chatwoot_tools schemas.py tests
```

A instalação acima é somente para os testes do plugin. Registrar a versão real instalada e o SHA efetivo do checkout. Não confundir esse interpretador com o que roda Hermes em VPS.

## Instalação do plugin no perfil de homologação

```bash
# Executar no host Hermes somente após criar e aprovar o perfil de destino.
hermes -p <PERFIL_DESTINO> plugins install ital-leste/hermes-chatwoot-plugin --ref <SHA_HOMOLOG_VALIDADO>
hermes -p <PERFIL_DESTINO> plugins enable chatwoot-tools
hermes -p <PERFIL_DESTINO> plugins doctor chatwoot-tools --ci

# Para diagnosticar a árvore de fontes: primeiro entrar no checkout do plugin.
cd /caminho/para/hermes-chatwoot-plugin
hermes -p <PERFIL_DESTINO> plugins validate .
hermes -p <PERFIL_DESTINO> plugins doctor . --ci
```

Registrar o SHA definitivo no relatório da revisão e na execução de instalação. Não substituir por `main` ou por `homolog` sem fixar commit. O SDK precisa existir no ambiente real do Hermes, inclusive após reconstrução/atualização de ambiente gerenciado. O profile `default` de ferramentas administrativas não serve como homologação automática de um perfil restrito.

## Ensaios integrados controlados

- Configurar `base_url_env`, credenciais e `account_id` único por token; testar credencial inexistente e conta divergente antes da rede.
- Habilitar apenas leituras inicialmente: conversas, mensagens e contatos. Comparar envelopes originais e metadados com o Chatwoot real.
- Conferir também schema após adaptação pelo Hermes/provedor da sessão, com tipos anuláveis e objetos de atributos livres.
- Verificar roteamento correto por `(account_id, inbox_id, conversation_id)` e não confundir tríade válida com destino autorizado do lote.
- Só com autorização formal, testar nota privada, publicação de texto, status, etiquetas e contato; conferir autoria por token e ausência de duplicidade.
- Testar rotação/revogação das credenciais e restrições de ferramentas/terminal do perfil no host, separadamente do plugin.
- Registrar versões Hermes, SDK, plugin, Chatwoot, evidências, horários, recursos de testes e resultados, sem tokens.

**Não forçar 5xx ou falhas destrutivas em instalações reais.** Erros ambíguos são testados com MockTransport; quando ocorrerem naturalmente em integração, reconciliar antes de repetir. Não ativar automaticamente worker de publicação nem o atendimento autônomo.

Ver [solicitação de revisão independente](REVISAO_INDEPENDENTE_RC4.md).

## Fechamento F3 e diagnóstico de perfil

O padrão `(?![\\s\\S])` representa fim absoluto em expressões regulares Python e ECMA-262, evitando o casamento de `$` imediatamente antes de quebra de linha final. A validação Python continua autoritativa e os testes de contrato exercitam email/telefone terminados por `\\n` sem chamada HTTP. Confirmar a adaptação do schema no provedor/modelo escolhido durante a homologação.

Os comandos `plugins validate .` e `plugins doctor . --ci` exigem que `.` seja o checkout real do plugin. Após instalação por SHA, prefira `plugins doctor chatwoot-tools --ci` no perfil explicitamente selecionado. Jamais presumir que `plugins install` mudou o diretório de trabalho ou que o perfil default foi selecionado corretamente.
