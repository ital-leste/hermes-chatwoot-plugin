# Hermes Chatwoot Plugin

Plugin nativo para o Hermes Agent que disponibiliza ferramentas da Application API do Chatwoot por meio da biblioteca Python externa `chatwoot_client`. Não contém regras de negócio ou parâmetros de uma organização específica.

**Estado:** `0.2.0rc4` em homologação corretiva; regressões incluem doubles e SDK real com HTTP simulado. **Não há homologação de leitura/escrita no Chatwoot real nem instalação operacional do plugin.** Esta versão altera o contrato de ferramentas da v0.1 (incompatível com chamadas antigas que usavam `installation`).

## Arquitetura e identidade

- **Uma instalação Chatwoot por perfil Hermes**: `base_url_env` aponta para a URL no `.env` do perfil; `credentials` relaciona as identidades de usuários autorizados aos nomes das variáveis de token, também do perfil.
- **Vários tokens na mesma instalação e conta** são permitidos (ex.: `atendimento`, `operador_a`, `operador_b`); cada ferramenta exige `credential`, que escolhe uma identidade explicitamente autorizada na configuração, não o valor do token.
- **Sem aliases de instalações, sem `.env` do plugin** e sem valores de token/URL nos argumentos de ferramenta. Perfis distintos podem usar URLs e tokens diferentes.
- Operações de conversa exigem `account_id`, `inbox_id`, `conversation_id`. O plugin consulta o Chatwoot e comprova a associação antes de ler ou escrever.
- Pesquisas de conversas exigem `account_id` e `inbox_id`; pesquisas de contatos usam essa dupla, e operações sobre contatos exigem `contact_id` adicional.
- Uma tríade válida não prova que o modelo escolheu a conversa pretendida pelo evento do consumidor. A autorização por sessão, idempotência, handoff e políticas de atendimento continuam fora do plugin.
- Consultas individuais devolvem o JSON original da API dentro de `data`, inclusive envelopes `payload` e metadados. **Pesquisas e históricos por inbox** preservam o formato e todos os campos dos itens autorizados, mas excluem recursos de outras inboxes. Contagens nativas podem refletir a busca anterior ao filtro. A visão interna para validação não substitui o JSON devolvido ao agente.
- O plugin não abre servidor, não persiste dados, não importa Evolution API e não executa HTTP Chatwoot sem `chatwoot_client`.

## Configuração do perfil

No `config.yaml` do perfil Hermes que executa o plugin:

```yaml
plugins:
  enabled:
    - chatwoot-tools
  entries:
    chatwoot-tools:
      settings:
        base_url_env: CHATWOOT_BASE_URL
        credentials:
          atendimento:
            token_env: CHATWOOT_ATENDIMENTO_TOKEN
            account_id: 7
          operador_a:
            token_env: CHATWOOT_OPERADOR_A_TOKEN
            account_id: 7
          operador_b:
            token_env: CHATWOOT_OPERADOR_B_TOKEN
            account_id: 7
        allow_insecure_http: false
        allowed_operations:
          conversation.read: true
          conversation.list: true
          messages.read: true
          messages.send_public: true
          # messages.send_private: true
          conversation.status.update: true
          conversation.labels.add: true
          conversation.labels.remove: true
          contacts.search: true
          contacts.read: true
          contacts.conversations.read: true
          contacts.update: true
        writable_contact_fields:
          name: true
          phone_number: true
          # email: true
          # identifier: true
          # blocked: true
          # avatar_url: true
          # additional_attributes: true
          # custom_attributes: true
```

O operador cadastra os valores no `.env` do perfil (ex.: `~/.hermes/profiles/atendimento/.env`):

```dotenv
CHATWOOT_BASE_URL=https://chatwoot.exemplo.com
CHATWOOT_ATENDIMENTO_TOKEN=<token_atendimento>
CHATWOOT_OPERADOR_A_TOKEN=<token_operador_a>
CHATWOOT_OPERADOR_B_TOKEN=<token_operador_b>
```

Os valores entre `<...>` são apenas exemplos e devem ser substituídos. O plugin chama `agent.secret_scope.get_secret(nome)` para ler a URL e o token no escopo do perfil. **Não armazene tokens no YAML, no Git ou nos argumentos das ferramentas.** A configuração do perfil e o mecanismo de segredos do Hermes são a fonte de autoridade; não há arquivo `.env` no repositório do plugin. Após editar arquivos do perfil, confirme se a versão do Hermes exige reinício/reload da sessão para aplicar as alterações.

Adicionar uma identidade requer incluir uma entrada em `credentials` e a variável correspondente no `.env` do perfil; remover a entrada revoga imediatamente a seleção daquela identidade assim que a configuração atualizada for carregada. Rotacionar um token não exige alterar o código. Cada credencial possui exatamente um `account_id` autorizado (inteiro positivo); o plugin compara esse valor ao parâmetro explícito da ferramenta antes de qualquer chamada HTTP.

Remover/comentar uma permissão é equivalente a `false`. Operações não declaradas são negadas. Atualizações de contato negam o payload inteiro quando inclui qualquer campo não autorizado.

HTTPS é obrigatório fora de loopback, salvo `allow_insecure_http: true` definido pelo operador em rede interna controlada. O nome de uma máquina em VPN não é automaticamente considerado loopback.

## Ferramentas (13)

| Ferramenta | Operação autorizadora | IDs obrigatórios (além de `credential`) |
| --- | --- | --- |
| `chatwoot_get_conversation` | `conversation.read` | account, inbox, conversation |
| `chatwoot_list_conversations` | `conversation.list` | account, inbox |
| `chatwoot_list_messages` | `messages.read` | account, inbox, conversation |
| `chatwoot_send_public_message` | `messages.send_public` | account, inbox, conversation |
| `chatwoot_send_private_note` | `messages.send_private` | account, inbox, conversation |
| `chatwoot_set_status` | `conversation.status.update` | account, inbox, conversation |
| `chatwoot_add_labels` | `conversation.labels.add` | account, inbox, conversation |
| `chatwoot_remove_labels` | `conversation.labels.remove` | account, inbox, conversation |
| `chatwoot_search_contacts` | `contacts.search` | account, inbox |
| `chatwoot_get_contact` | `contacts.read` | account, inbox, contact |
| `chatwoot_get_contact_conversations` | `contacts.conversations.read` | account, inbox, contact |
| `chatwoot_update_contact` | `contacts.update` | account, inbox, contact |

Exemplo de publicação:

```json
{"credential": "atendimento", "account_id": 7, "inbox_id": 4, "conversation_id": 482, "content": "Bom dia!"}
```

O plugin resolve `credential` no mapa autorizado, confere a igualdade do `account_id` com o único `account_id` da credencial, recupera o token pelo nome da variável e então confere a associação com `conversations.get()` e só então chama `messages.send_text()` do cliente. Não garante entrega no WhatsApp após HTTP 2xx. Falhas dentro de método potencialmente modificador, inclusive HTTP 2xx com JSON inválido, HTTP 5xx ou timeout, podem devolver `outcome_unknown`; não repetir sem reconciliação. Em etiquetas o método pode concluir após GET sem POST, de modo que `outcome_unknown` é conservador e **não comprova transmissão**. Sucesso HTTP também não comprova entrega externa.

Veja [Ferramentas](docs/FERRAMENTAS.md), [Configuração](docs/CONFIGURACAO.md) e [Arquitetura](docs/ARQUITETURA.md).

## Limites da escolha de usuário

`credential` é uma **identidade de autenticação configurada**, não uma prova de que a pessoa correspondente solicitou a operação. Um agente que possua as credenciais `operador_a` e `operador_b` habilitadas poderá selecionar qualquer uma delas. Para exigir que determinado atendimento utilize apenas uma identidade, restrinja as entradas de `credentials` disponibilizadas ao perfil ou vincule a identidade por um consumidor confiável; a v0.2rc5 ainda não realiza autorização por sessão.

O Chatwoot determina a autoria efetiva da operação a partir do token autenticado e das permissões reais. O identificador `credential` não é o nome de usuário verificado pelo plugin. Para conferir a autoria, utilize os dados do servidor em uma homologação real.

Veja [Segurança do perfil](docs/SEGURANCA_PERFIL.md) para as configurações de execução de comandos e proteção dos segredos.

## Instalação e limitação de distribuição

Para homologação, utilizar a revisão imutável aprovada. Substitua `<SHA_HOMOLOG_VALIDADO>` pelo SHA completo registrado no **relatório do commit final**, não tente colocar o SHA do próprio commit dentro deste README:

```bash
# Para habilitar o plugin, selecione explicitamente o perfil de destino:
hermes -p <PERFIL_DESTINO> plugins install ital-leste/hermes-chatwoot-plugin --ref <SHA_HOMOLOG_VALIDADO>
hermes -p <PERFIL_DESTINO> plugins enable chatwoot-tools
hermes -p <PERFIL_DESTINO> plugins list
hermes -p <PERFIL_DESTINO> plugins doctor chatwoot-tools --ci

# Somente em um checkout local do plugin, a partir de seu diretório-raiz:
cd /caminho/para/hermes-chatwoot-plugin
hermes -p <PERFIL_DESTINO> plugins validate .
hermes -p <PERFIL_DESTINO> plugins doctor . --ci
```

A sintaxe `-p` seleciona o perfil para esta chamada sem alterar o perfil padrão. Antes da instalação, confirme no Hermes instalado que os comandos e a opção `-p` são suportados e que o perfil foi criado. Não ative inadvertidamente no perfil `default`.

**Distribuição pendente:** a biblioteca independente que fornece o módulo `chatwoot_client` ainda não possui uma distribuição versionada confirmada e licenciada num índice Python compatível com o gerenciador Hermes. Por isso, o manifesto do plugin mantém `dependencies = []` temporariamente.

Para homologação controlada, provisione o SDK externo no **mesmo interpretador/processo Python utilizado pelo Hermes** a partir de um checkout com SHA identificado; registre o SHA e como a instalação persiste após rebuild do ambiente:

```bash
python -m pip install "git+https://github.com/ital-leste/chatwoot-client.git@ef7254b5e45d27e710e23a4c6bc255f55d147206"
python -c "from chatwoot_client import CWClient; print('OK')"
```

O comando acima é de **provisionamento de homologação** e precisa ser executado no ambiente efetivo do Hermes, não em um terminal/venv diferente. O pacote instalado deve disponibilizar `chatwoot_client`; não substitua por qualquer pacote homônimo sem verificar a API. A dependência formal será declarada somente depois da publicação de uma versão compatível em um índice autorizado. Esse requisito permanece pendente, assim como a homologação nativa em uma instalação real.

## Testes e homologação

```bash
python -m pip install 'pytest==9.2.0' 'PyYAML==6.0.3' 'jsonschema==4.26.0'
python -m pytest -q
```

Os testes unitários usam doubles; as regressões adicionais exercitam o SDK `chatwoot_client` real com `httpx.MockTransport` sem rede. Isso não comprova integração real com Hermes/Chatwoot. A representação final dos schemas após adaptação pelo Hermes/provedor também exige verificação no runtime alvo. A validação integrada deve ser feita com credenciais de teste e autorização explícita, iniciando por permissões somente de leitura. Ver [Plano de homologação](docs/HOMOLOGACAO.md).

## Documentação

- [Arquitetura](docs/ARQUITETURA.md)
- [Configuração e segurança](docs/CONFIGURACAO.md)
- [Contratos das ferramentas](docs/FERRAMENTAS.md)
- [Homologação](docs/HOMOLOGACAO.md)
- [Segurança do perfil Hermes](docs/SEGURANCA_PERFIL.md)
- [Histórico de versões](CHANGELOG.md)
- [Solicitação de revisão independente rc4](docs/REVISAO_INDEPENDENTE_RC4.md)


## Mídias (RC5): imagens, PDF, vídeo e áudio

A ferramenta `chatwoot_send_media` publica **um único anexo público** com legenda opcional,
por meio de `CWClient.messages.send_media`. Ela aceita apenas **URL HTTPS**,
nunca caminho local, bytes ou arquivos fornecidos diretamente pelo modelo.
A origem precisa constar exatamente na lista `media_allowed_hosts` configurada pelo administrador;
sem lista, a operação falha mesmo se `messages.send_media=true`.
O SDK limita a transferência a 15 MiB, valida IPs públicos e recusa redirecionamentos.
Os MIME autorizados são PNG/JPEG/WebP/GIF, PDF, MP4/WebM, MP3/OGG/WAV e áudio MP4.
`is_voice_message=true` requer `audio/ogg`; áudio comum pode ser enviado como anexo.
A ferramenta mantém os identificadores obrigatórios de conta, inbox e conversa, antes da escrita.

Exemplo de configuração do perfil (sem qualquer segredo):
```yaml
plugins:
  entries:
    chatwoot-tools:
      settings:
        media_allowed_hosts: ["midia.example.com"]
        allowed_operations:
          messages.send_media: true
```

Exemplo de argumentos da ferramenta:
```json
{"credential":"atendimento","account_id":7,"inbox_id":4,"conversation_id":482,"media_url":"https://midia.example.com/exemplo.ogg","mime_type":"audio/ogg","filename":"exemplo.ogg","is_voice_message":true}
```

O resultado `outcome_unknown` indica possível escrita já realizada; não repetir sem reconciliar.
A ferramenta de mídias não amplia permissão de terminal, arquivos, navegador ou HTTP arbitrário.
