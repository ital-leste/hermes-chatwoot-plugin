import pytest


def test_https_e_loopback(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    from hermes_chatwoot_v02_tests.chatwoot_tools.connection import resolve_connection
    config = parse_config(cfg)
    assert resolve_connection(config, config.credentials["atendimento"],
        lambda key: {"CHATWOOT_BASE_URL":"https://chatwoot.exemplo.com", "CHATWOOT_ATENDIMENTO_TOKEN":"token"}[key])[0] == "https://chatwoot.exemplo.com"
    for url in ("http://127.0.0.1:3000", "http://[::1]:3000"):
        assert resolve_connection(config, config.credentials["atendimento"],
            lambda key, url=url: url if key == "CHATWOOT_BASE_URL" else "token")[0] == url


def test_http_externo_bloqueado(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    from hermes_chatwoot_v02_tests.chatwoot_tools.errors import ConfigurationError
    from hermes_chatwoot_v02_tests.chatwoot_tools.connection import resolve_connection
    parsed = parse_config(cfg)
    def scoped(name):
        return "http://chatwoot.interno:3000" if name == "CHATWOOT_BASE_URL" else "token"
    with pytest.raises(ConfigurationError):
        resolve_connection(parsed, parsed.credentials["atendimento"], scoped)
    cfg["allow_insecure_http"]=True
    parsed = parse_config(cfg)
    assert resolve_connection(parsed, parsed.credentials["atendimento"], scoped)[0] == "http://chatwoot.interno:3000"


@pytest.mark.parametrize("key,value", [
    ("allow_insecure_http", "true"),
    ("allowed_operations", {"conversation.read":"true"}),
    ("allowed_operations", {"unknown":True}),
    ("writable_contact_fields", {"not_real":True}),
    ("writable_contact_fields", {"email":1}),
])
def test_config_invalida(plugin,cfg,key,value):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    from hermes_chatwoot_v02_tests.chatwoot_tools.errors import ConfigurationError
    cfg[key]=value
    with pytest.raises(ConfigurationError): parse_config(cfg)


def test_flags_negam_ausencia_comentario_false(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    cfg["allowed_operations"]={"messages.read":True,"messages.send_public":False}
    p=parse_config(cfg)
    assert p.operations==frozenset({"messages.read"})
    assert p.writable_fields==frozenset({"name", "phone_number"})


@pytest.mark.parametrize("bad", [
    {"operador_a": {"token_env": "lowercase", "account_id": 17}},
    {"operador_a": {"token_env": "CHATWOOT_OPERADOR_A_TOKEN", "account_id": 0}},
    {"operador_a": {"token_env": "CHATWOOT_OPERADOR_A_TOKEN", "account_id": True}},
    {"operador_a": {"token_env": "CHATWOOT_OPERADOR_A_TOKEN", "account_id": [17]}},
    {"operador_a": {"token_env": "CHATWOOT_OPERADOR_A_TOKEN"}},
    {"operador_a": {"token_env": "CHATWOOT_OPERADOR_A_TOKEN", "account_id": 17, "token": "segredo"}},
    {"operador_a": {"token_env": "CHATWOOT_OPERADOR_A_TOKEN", "allowed_account_ids": [17]}},
    {"in valid": {"token_env": "CHATWOOT_OPERADOR_A_TOKEN", "account_id": 17}},
    {},
])

def test_credenciais_invalidas_fail_closed(plugin, cfg, bad):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    from hermes_chatwoot_v02_tests.chatwoot_tools.errors import ConfigurationError
    cfg["credentials"] = bad
    with pytest.raises(ConfigurationError):
        parse_config(cfg)


def test_variavel_url_invalida(plugin, cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    from hermes_chatwoot_v02_tests.chatwoot_tools.errors import ConfigurationError
    cfg["base_url_env"] = "CHATWOOT;rm -rf"
    with pytest.raises(ConfigurationError): parse_config(cfg)


def test_token_env_nao_pode_repetir_url_ou_outro_token(plugin, cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    from hermes_chatwoot_v02_tests.chatwoot_tools.errors import ConfigurationError
    cfg["credentials"]["operador_a"]["token_env"] = cfg["base_url_env"]
    with pytest.raises(ConfigurationError): parse_config(cfg)
    cfg["credentials"]["operador_a"]["token_env"] = cfg["credentials"]["atendimento"]["token_env"]
    with pytest.raises(ConfigurationError): parse_config(cfg)
