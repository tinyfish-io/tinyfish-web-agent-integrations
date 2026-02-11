from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class TinyfishWebAgentProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        api_key = credentials.get("api_key")
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            raise ToolProviderCredentialValidationError("API key is required")
