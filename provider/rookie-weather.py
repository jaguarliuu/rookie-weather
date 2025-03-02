from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from tools.gaode_weather import GaodeWeatherTool


class RookieWeatherProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            """
            IMPLEMENT YOUR VALIDATION HERE
            """
            for _ in GaodeWeatherTool.from_credentials(credentials).invoke(
                tool_parameters={"city":"西安"}  
            ):
                pass
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))
