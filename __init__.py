"""Entrada oficial do plugin Hermes Chatwoot Tools."""
from __future__ import annotations

# O carregador do Hermes importa este diretório como pacote. Pytest pode importar
# o __init__.py da raiz sem contexto de pacote durante a descoberta dos testes.
if __package__:
    from .chatwoot_tools.service import ToolService
    from .schemas import SCHEMAS
    from .tools import handler_for


def register(ctx) -> None:
    """Registra ferramentas estáticas; autorização é avaliada a cada execução."""
    service = ToolService(lambda: ctx.get_config("installations", default={}))
    for name, tool_schema in SCHEMAS.items():
        ctx.register_tool(
            name=name,
            toolset="chatwoot_tools",
            schema=tool_schema,
            handler=handler_for(service, name),
        )
