"""Falhas estáveis do adaptador, sem mensagens que exponham segredos."""
from __future__ import annotations


class PluginError(Exception):
    code = "plugin_error"


class ConfigurationError(PluginError):
    code = "invalid_configuration"


class AuthorizationError(PluginError):
    code = "operation_denied"


class ScopeError(PluginError):
    code = "scope_denied"


class ArgumentsError(PluginError):
    code = "invalid_arguments"


class CredentialsError(PluginError):
    code = "credentials_unavailable"


class DependencyError(PluginError):
    code = "client_unavailable"
