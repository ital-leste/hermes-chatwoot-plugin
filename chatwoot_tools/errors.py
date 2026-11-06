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


class PreWriteError(PluginError):
    """Falha comprovada antes de iniciar a escrita."""


class MediaUnavailableError(PreWriteError):
    code = "media_unavailable"


class MediaRedirectRejectedError(PreWriteError):
    code = "media_redirect_rejected"


class PaginationError(PluginError):
    code = "pagination_incomplete"
