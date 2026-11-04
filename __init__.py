"""Entrada pública do plugin nativo do Hermes."""
from __future__ import annotations

if __package__:
    from .chatwoot_tools.service import ToolService
    from .schemas import SCHEMAS
    from .tools import handler_for


def register(ctx) -> None:
    """Registra ferramentas: sem conexão HTTP e sem acesso a segredos no startup."""
    def settings():
        return {
            "base_url_env": ctx.get_config("base_url_env", default=None),
            "credentials": ctx.get_config("credentials", default={}),
            "allow_insecure_http": ctx.get_config("allow_insecure_http", default=False),
            "allowed_operations": ctx.get_config("allowed_operations", default={}),
            "writable_contact_fields": ctx.get_config("writable_contact_fields", default={}),
        }

    service = ToolService(settings)
    for name, schema in SCHEMAS.items():
        ctx.register_tool(name=name, toolset="chatwoot_tools", schema=schema,
                          handler=handler_for(service, name))
