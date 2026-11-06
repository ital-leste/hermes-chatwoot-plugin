"""G3: ferramenta de midia (imagem, PDF, video, audio e voz)."""
import json
import pytest


def chamar(svc, **overrides):
    payload = {
        "credential": "atendimento", "account_id": 17, "inbox_id": 4,
        "conversation_id": 482,
        "media_url": "https://midia.example.com/teste.png",
        "mime_type": "image/png", "filename": "teste.png", "caption": "Legenda",
    }
    payload.update(overrides)
    return json.loads(svc.execute("chatwoot_send_media", payload))


@pytest.mark.parametrize("mime,filename,voice", [
    ("image/png", "img.png", False),
    ("application/pdf", "arquivo.pdf", False),
    ("video/mp4", "video.mp4", False),
    ("audio/mpeg", "audio.mp3", False),
    ("audio/wav", "audio.wav", False),
    ("audio/ogg", "audio.ogg", False),
    ("audio/ogg", "audio.ogg", True),
])
def test_media_somente_com_dupla_autorizacao(svc, cfg, factory, mime, filename, voice):
    cfg["allowed_operations"]["messages.send_media"] = True
    cfg["media_allowed_hosts"] = ["midia.example.com"]
    result = chamar(
        svc, mime_type=mime, filename=filename,
        is_voice_message=voice,
    )
    assert result["success"]
    assert result["operation"] == "messages.send_media"
    calls = factory.clients[0].calls
    assert [x[0] for x in calls] == ["conversation.get", "messages.send_media"]
    message, extra = calls[-1][3:]
    assert message.attachments[0].mime_type == mime
    assert message.attachments[0].filename == filename
    assert message.attachments[0].source.startswith("https://")
    assert message.caption == "Legenda"
    assert message.private is False
    assert message.is_voice_message is voice
    assert extra["max_bytes"] == 15 * 1024 * 1024
    assert extra["allowed_hosts"] == frozenset({"midia.example.com"})


def test_sem_permissao_negado_antes_de_http(svc, factory):
    result = chamar(svc)
    assert result["error"]["code"] == "operation_denied"
    assert not factory.clients


def test_sem_allowlist_rejeita_antes_de_http(svc, cfg, factory):
    cfg["allowed_operations"]["messages.send_media"] = True
    result = chamar(svc)
    assert result["error"]["code"] == "operation_denied"
    assert not factory.clients


@pytest.mark.parametrize("url", [
    "http://midia.example.com/a.png",
    "file:///etc/passwd",
    "/etc/passwd",
    "https://user:secret@midia.example.com/a.png",
    "https://127.0.0.1/a.png",
    "https://midia.example.com:8443/a.png",
    "https://outro.example.com/a.png",
])
def test_fonte_indevida_rejeitada_sem_escrita(svc, cfg, factory, url):
    cfg["allowed_operations"]["messages.send_media"] = True
    cfg["media_allowed_hosts"] = ["midia.example.com"]
    result = chamar(svc, media_url=url)
    assert result["success"] is False
    assert not any(
        any(x[0] == "messages.send_media" for x in client.calls)
        for client in factory.clients
    )


@pytest.mark.parametrize("payload", [
    {"mime_type": "application/x-executable"},
    {"filename": "../../segredo.txt"},
    {"filename": "C:\\segredo.txt"},
    {"filename": "linha\nquebrada.png"},
    {"is_voice_message": True},
    {"is_voice_message": "true"},
    {"caption": []},
])
def test_contrato_invalido_bloqueado_antes_http(svc, cfg, factory, payload):
    cfg["allowed_operations"]["messages.send_media"] = True
    cfg["media_allowed_hosts"] = ["midia.example.com"]
    result = chamar(svc, **payload)
    assert result["error"]["code"] in {"invalid_arguments", "operation_denied"}
    assert not factory.clients


def test_conta_inbox_erradas_bloqueiam_media(svc, cfg, factory):
    cfg["allowed_operations"]["messages.send_media"] = True
    cfg["media_allowed_hosts"] = ["midia.example.com"]
    assert chamar(svc, account_id=18)["error"]["code"] == "scope_denied"
    assert chamar(svc, inbox_id=999)["error"]["code"] == "scope_denied"
    assert not any(
        x[0] == "messages.send_media"
        for client in factory.clients for x in client.calls
    )


def test_falha_apos_chamada_retorna_outcome_unknown(svc, cfg, factory):
    cfg["allowed_operations"]["messages.send_media"] = True
    cfg["media_allowed_hosts"] = ["midia.example.com"]
    c = factory.make("https://chatwoot.exemplo.com", "token_value")
    c.fail = TimeoutError("secret-memory")
    svc.client_factory = lambda *a: c
    result = chamar(svc)
    # Uma falha pode ocorrer na validacao da conversa, quando nao houve escrita.
    assert result["error"]["code"] in {"execution_error", "outcome_unknown"}
    assert "secret-memory" not in json.dumps(result)


def test_config_allowlist_deve_ser_explicita(plugin):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    from hermes_chatwoot_v02_tests.chatwoot_tools.errors import ConfigurationError
    base = {
        "base_url_env": "CHATWOOT_BASE_URL",
        "credentials": {"atendimento": {"token_env": "CHATWOOT_TOKEN", "account_id": 1}},
        "allowed_operations": {"messages.send_media": True},
    }
    assert not parse_config(base).media_allowed_hosts
    for bad in (["*"], ["localhost"], ["127.0.0.1"], ["UPPER.example.com"], ["a.example.com", "a.example.com"], "example.com"):
        with pytest.raises(ConfigurationError):
            parse_config({**base, "media_allowed_hosts": bad})
    parsed = parse_config({**base, "media_allowed_hosts": ["midia.example.com"]})
    assert parsed.media_allowed_hosts == frozenset({"midia.example.com"})
