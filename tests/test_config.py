from __future__ import annotations

import copy
import pytest


def parser(plugin):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.config import parse_installations
    return parse_installations


def test_config_multipla_e_escopos(configured, plugin):
    data = parser(plugin)(configured)
    assert set(data) == {"principal", "homolog"}
    assert data["principal"].inbox_ids == frozenset({4, 6})
    assert data["homolog"].inbox_ids is None
    assert data["principal"].operations.isdisjoint({"messages.send_private"})
    assert data["homolog"].operations == {"messages.read"}


@pytest.mark.parametrize("change", [
    lambda c: c["principal"].update({"token_env": ""}),
    lambda c: c["principal"].update({"base_url": "ftp://bad.example"}),
    lambda c: c["principal"].update({"base_url": "https://user:pass@host.invalid"}),
    lambda c: c["principal"].update({"base_url": "https://host.invalid?token=a"}),
    lambda c: c["principal"].update({"allowed_account_ids": []}),
    lambda c: c["principal"].update({"allowed_account_ids": [True]}),
    lambda c: c["principal"].update({"allowed_account_ids": [17, 17]}),
    lambda c: c["principal"].update({"allowed_inbox_ids": "all"}),
    lambda c: c["principal"].update({"allowed_inbox_ids": [4, False]}),
    lambda c: c["principal"].update({"allowed_operations": {"messages.send_public": "true"}}),
    lambda c: c["principal"].update({"allowed_operations": {"messages.delete": True}}),
    lambda c: c["principal"].update({"unexpected": "value"}),
])
def test_config_invalida_falha_fechada(configured, plugin, change):
    from hermes_chatwoot_plugin_tests.chatwoot_tools.errors import ConfigurationError
    cfg = copy.deepcopy(configured)
    change(cfg)
    with pytest.raises(ConfigurationError):
        parser(plugin)(cfg)


def test_config_sem_operacoes_nega_tudo(configured, plugin):
    configured["principal"].pop("allowed_operations")
    assert not parser(plugin)(configured)["principal"].operations


def test_inbox_vazia_negar_tudo(configured, plugin):
    configured["principal"]["allowed_inbox_ids"] = []
    assert parser(plugin)(configured)["principal"].inbox_ids == frozenset()


def test_alias_invalido(configured, plugin):
    configured["alias.dot"] = configured.pop("homolog")
    from hermes_chatwoot_plugin_tests.chatwoot_tools.errors import ConfigurationError
    with pytest.raises(ConfigurationError):
        parser(plugin)(configured)
