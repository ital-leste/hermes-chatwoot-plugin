from __future__ import annotations

from pathlib import Path
import json
import yaml


def test_manifesto_e_esquemas_sincronizados(plugin):
    root=Path(__file__).resolve().parents[1]
    manifest=yaml.safe_load((root / "plugin.yaml").read_text())
    assert manifest["name"]=="chatwoot-tools"
    assert set(manifest["provides_tools"])==set(plugin.SCHEMAS)
    for key, schema in plugin.SCHEMAS.items():
        assert key==schema["name"]
        assert schema["parameters"]["additionalProperties"] is False
        assert {"installation","account_id","conversation_id"}.issubset(schema["parameters"]["required"])


def test_registro_nativo_e_falha_fechada_sem_config(plugin):
    class Context:
        def __init__(self):
            self.handlers={}
        def get_config(self, name, default=None):
            assert name=="installations"
            return default
        def register_tool(self,*,name,toolset,schema,handler):
            assert toolset=="chatwoot_tools"
            assert schema["name"]==name
            self.handlers[name]=handler
    ctx=Context()
    plugin.register(ctx)
    assert len(ctx.handlers)==7
    r=json.loads(ctx.handlers["chatwoot_get_conversation"]({"installation":"x","account_id":1,"conversation_id":1}, task_id="test"))
    assert r["error"]["code"]=="invalid_configuration"
