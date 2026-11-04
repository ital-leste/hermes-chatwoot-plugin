# Homologação v0.2.0rc2

## Estado

Suite unitária simulada; não equivale a validação Hermes/Chatwoot real. Homologação integrada é obrigatória antes de liberar escrita em produção.

## CI e checagens estáticas

```bash
python -m pip install 'pytest>=8,<10' 'PyYAML>=6,<7'
python -m pytest -q
python -m compileall -q .
```

Cobertura: manifesto/12 ferramentas, resolução de URL por variável, múltiplos tokens e identidades, criação/remoção/rotação de credenciais, escopo por conta, segredo sem exposição ao modelo, triade obrigatória, inbox divergente bloqueando escrita, payload nativo, lista/consulta de contatos e associação de inbox, rejeição de campos não liberados, HTTP seguro, comentários/false, timeout de guarda e timeout após escrita, fechamento do cliente e ausência de rede em registro do plugin.

## Teste no Hermes instalado

1. Instalar o cliente correto `ital-leste/chatwoot-client` **no interpretador utilizado pelo Hermes** (dependência temporariamente manual; não instalar um pacote homônimo do PyPI).
2. Instalar o plugin em ambiente de teste e confirmar `hermes plugins validate .` e `hermes plugins doctor . --ci` no próprio runtime.
3. Configurar `base_url_env` e `credentials` no `config.yaml` e os valores correspondentes no `.env` do perfil Hermes. Verificar que tokens não aparecem no YAML, nos argumentos das ferramentas ou nos retornos.
4. Autorizar inicialmente só `conversation.read`, `conversation.list`, `messages.read`, `contacts.read` e `contacts.search`. Cadastrar inicialmente uma credencial de teste com seu escopo de contas.
5. Testar conta, inbox e conversa válidos e divergentes; confirmar ausência de escrita ao divergir.
6. Pesquisar contatos presentes em uma e em várias inboxes; inspecionar o formato real dos endpoints, especialmente `contact_inboxes` e a lista de conversas.
7. Confirmar que uma atualização de contato altera o cadastro compartilhado da conta e que a política de campos impede alterações proibidas.
8. Autorizar notas privadas antes de mensagens públicas; verificar a materialização com clientes de teste.
9. Testar status, etiquetas e comportamento não atômico de GET+POST.
10. Validar HTTPS e exceção explícita HTTP numa rede interna controlada.
11. Validar `italbot`, `luiz` e `marcio` na mesma instalação: tokens distintos, mesma conta quando autorizado, atribuição de autoria correta no Chatwoot; validar conta não autorizada, identidade inexistente, criação, rotação e remoção de credencial.
12. Validar um segundo perfil Hermes em processo/ambiente separado com outra URL/tokens e as mesmas IDs internas; confirmar isolamento.
13. Confirmar que o perfil de atendimento não dispõe de execução arbitrária de comandos, leitura de arquivos ou administração; essas restrições são do Hermes/host, não do plugin. Ver [Segurança do perfil](SEGURANCA_PERFIL.md).
14. Registrar SHA do plugin/cliente, versões Hermes/Chatwoot, evidências e resultado de cada operação.

## Gates de promoção

- CI aprovado (3.11, 3.12, 3.13).
- Hermes `validate` e `doctor` aprovados em versão alvo, com segredo funcional.
- Testes de leitura e escrita reais executados e documentados.
- Biblioteca Chatwoot Client formalmente versionada e publicada em índice acessível, com licença aprovada e dependência do plugin declarada no `pyproject.toml`.

**A publicação da biblioteca e a licença ainda não estão concluídas.** Não declarar a dependência automática nem uso produtivo homologados antes de concluir esses gates.
