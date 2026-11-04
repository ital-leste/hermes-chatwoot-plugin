# Configuração e segurança

O plugin usa o namespace nativo `plugins.entries.chatwoot-tools.settings` do Hermes. Não há instalações nomeadas nem `.env` dentro do plugin.

```yaml
plugins:
  entries:
    chatwoot-tools:
      settings:
        base_url: "https://chatwoot.exemplo.com"
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

### URL e credencial

- `base_url`: configura a instalação atendida por este perfil Hermes. URL HTTPS é obrigatória por padrão fora de loopback (`localhost`, `127.0.0.0/8`, `::1`).
- `allow_insecure_http`: exceção explícita `true` para HTTP numa rede privada confiável. Nunca inferir segurança somente do hostname.
- `api_token`: no `plugin.yaml`, campo `type: secret` associado a `CHATWOOT_API_TOKEN`. O segredo **não** é armazenado como valor no `config.yaml`. Deve ser configurado via gerenciador de segredos ou ambiente protegido do perfil, e resolvido por `agent.secret_scope.get_secret()`.
- Um segundo perfil Hermes pode ter URL e token próprios. Em um único processo com perfis que compartilham o ambiente do SO, variáveis de mesmo nome podem não estar isoladas; validar o runtime. Para isolamento forte, operar perfis em ambientes/processos segregados.

### Autorização

- Toda operação ausente ou declarada `false` é negada; nomes desconhecidos ou valores não booleanos invalidam toda a configuração.
- `writable_contact_fields` é uma allowlist independente da permissão `contacts.update`. O plugin rejeita a atualização inteira se qualquer chave solicitada não estiver liberada; não aplica atualizações parciais silenciosamente.
- A autorização do plugin restringe, mas não substitui, as permissões do token no Chatwoot. A tríade deve ser verificada em cada operação de conversa.
- Nenhuma ferramenta recebe URL ou token do modelo. Token não aparece em JSON de sucesso/erro nem em exceções devolvidas à LLM.

### HTTP e HTTPS

`https://...` é permitido. `http://127.0.0.1:3000` e `http://[::1]:3000` são permitidos sem exceção. `http://chatwoot-interno:3000` exige `allow_insecure_http: true`. O operador é responsável por TLS, VPN e controle de acesso à rede.

### Retorno integral

O plugin preserva o JSON retornado pelo cliente nos resultados de leitura/publicação. Em buscas restritas à inbox, retorna apenas os recursos cuja associação foi comprovada, com os **campos originais** preservados. Não há redução por privacidade ou projeção de mensagens/contatos. Tokens, headers e exceções brutas seguem protegidos.
