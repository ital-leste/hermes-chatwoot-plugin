# Plano de homologação da v0.1

## Testes automatizados sem credenciais

```bash
python -m pip install "pytest>=8,<10" "PyYAML>=6,<7"
python -m pytest -q
```

Os testes simulados cobrem: mapa de instalações, URL/token_env válidos, contas/inboxes e permissões separadas, comentário/ausência/`false`, rejeição de nomes de operação desconhecidos, argumentos inválidos antes da rede, consulta de guarda por inbox, nota privada/publicação pública, status tipado, etiquetas, troca de configuração entre chamadas, JSON de saída, classificação de erros e registro dos sete schemas.

**Limitação:** o `CWClient` e o contexto Hermes são simulados. Esta aprovação demonstra apenas o comportamento local do plugin, não prova a instalação nativa no Hermes, permissões reais do servidor ou chegada de mensagens no canal externo.

## Validação estrutural no Hermes

Após instalar o plugin em um runtime Hermes que tenha `chatwoot_client` disponível:

```bash
# Executar na raiz do diretório de plugin
hermes plugins validate .
hermes plugins doctor . --ci
hermes plugins list
```

Validar: o nome no manifesto é `chatwoot-tools`; o `register(ctx)` registra exatamente as sete ferramentas; as ferramentas utilizam os schemas oficiais e retornam texto JSON; o plugin habilitado aparece no catálogo. Validar a versão e a compatibilidade do Hermes instalado, inclusive as APIs `ctx.get_config` e `agent.secret_scope.get_secret`.

## Integração real (manual e expressamente autorizada)

1. Configurar URL e token de uma instalação **de teste** com conta e inbox permitidas. Não registrar segredos no repositório ou em logs.
2. Permitir inicialmente apenas `conversation.read` e `messages.read`: consultar dados e verificar associação real da inbox.
3. Testar uma segunda instalação com outro alias, outra credencial e IDs coincidentes, conferindo isolamento.
4. Confirmar negação de conta proibida, inbox proibida, credencial ausente e operação comentada sem publicação.
5. Autorizar `messages.send_private` em uma conversa de teste, publicar uma nota interna e verificar sua visibilidade.
6. Autorizar `messages.send_public` somente mediante permissão explícita, enviar texto de teste e consultar sua materialização. **Não presumir entrega final WhatsApp**.
7. Exercitar estados `open`, `pending`, `resolved` e `snoozed`, incluindo `snoozed_until`, em conversa isolada.
8. Validar `conversation.labels.add/remove` e observar os riscos de concorrência das chamadas GET + POST.
9. Em 401/403/404/422, timeout e falhas de conexão, inspecionar o código de erro sem revelar dados e confirmar que não há repetição automática de escrita.
10. Registrar o SHA do plugin, SHA/versão do cliente, versão Hermes, versão Chatwoot, ambiente e evidências da execução.

**Gates de aceite:** CI verde; `doctor --ci` aprovado no Hermes-alvo; instalação do cliente verificada; operações de leitura reais aprovadas; escritas somente mediante autorização; resultados observados na conversa correta. A v0.1 não deve ser declarada homologada para produção sem os ensaios reais.
