import pytest


def test_https_e_loopback(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    assert parse_config(cfg).base_url=="https://chatwoot.exemplo.com"
    cfg["base_url"]="http://127.0.0.1:3000"
    assert parse_config(cfg).base_url=="http://127.0.0.1:3000"
    cfg["base_url"]="http://[::1]:3000"
    assert parse_config(cfg).base_url=="http://[::1]:3000"


def test_http_externo_bloqueado(plugin,cfg):
    from hermes_chatwoot_v02_tests.chatwoot_tools.config import parse_config
    from hermes_chatwoot_v02_tests.chatwoot_tools.errors import ConfigurationError
    cfg["base_url"]="http://chatwoot.interno:3000"
    with pytest.raises(ConfigurationError): parse_config(cfg)
    cfg["allow_insecure_http"]=True
    assert parse_config(cfg).base_url=="http://chatwoot.interno:3000"


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
