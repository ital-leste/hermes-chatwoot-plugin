import json
from pathlib import Path
import yaml


def test_manifesto_registro(plugin):
    root=Path(__file__).resolve().parents[1]
    m=yaml.safe_load((root/"plugin.yaml").read_text())
    assert set(m["provides_tools"])==set(plugin.SCHEMAS)
    assert m["config_schema"]["base_url_env"]["type"]=="str"
    assert m["config_schema"]["credentials"]["type"]=="dict"
    assert "api_token" not in m["config_schema"]
    for name, schema in plugin.SCHEMAS.items():
        assert schema["name"]==name
        assert "installation" not in schema["parameters"]["properties"]
        assert schema["parameters"]["additionalProperties"] is False
        assert {"credential","account_id","inbox_id"}.issubset(schema["parameters"]["required"])
        if "conversation_id" in schema["parameters"]["properties"]:
            assert "conversation_id" in schema["parameters"]["required"]


def test_registro_nao_conecta_ao_chatwoot(plugin):
    class Ctx:
        handlers={}
        def get_config(self,key,default=None):return default
        def register_tool(self,*,name,toolset,schema,handler):
            assert toolset=="chatwoot_tools"
            self.handlers[name]=handler
    ctx=Ctx()
    plugin.register(ctx)
    assert len(ctx.handlers)==12
    result=json.loads(ctx.handlers["chatwoot_get_conversation"]({"credential":"italbot","account_id":17,"inbox_id":4,"conversation_id":482},task_id="sessao1"))
    assert result["error"]["code"]=="invalid_configuration"
