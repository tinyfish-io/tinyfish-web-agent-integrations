from collections.abc import Generator
from typing import Any

import httpx
from dify_plugin.entities.tool import ToolInvokeMessage

from dify_plugin import Tool

from tools.base import TinyfishMixin


class RunSyncTool(TinyfishMixin, Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        if not tool_parameters.get("url"):
            yield self.create_text_message("Error: URL is required")
            return

        if not tool_parameters.get("goal"):
            yield self.create_text_message("Error: Goal is required")
            return

        payload = self._build_automation_payload(tool_parameters)

        try:
            response = self._tf_request(
                "POST", "/v1/automation/run", json=payload, timeout=300.0
            )

            result = response.json()
            status = result.get("status")

            if status == "COMPLETED":
                yield self.create_text_message("Automation completed successfully!")
                yield self.create_text_message(f"Run ID: {result.get('run_id')}")
                yield self.create_text_message(
                    f"Steps taken: {result.get('num_of_steps', 'N/A')}"
                )

                if result.get("result"):
                    yield self.create_json_message(result["result"])
                else:
                    yield self.create_text_message("No result data returned")
            elif status == "FAILED":
                error_info = result.get("error", {})
                error_message = (
                    error_info.get("message", "Unknown error")
                    if isinstance(error_info, dict)
                    else str(error_info)
                )
                yield self.create_text_message(f"Automation failed: {error_message}")
                yield self.create_text_message(f"Run ID: {result.get('run_id')}")
            else:
                yield self.create_json_message(result)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                yield self.create_text_message("Error: Invalid API key")
            else:
                yield self.create_text_message(
                    f"Error: API request failed with status {e.response.status_code}: {e.response.text}"
                )
        except httpx.TimeoutException:
            yield self.create_text_message(
                "Error: Request timed out. The automation may be taking too long."
            )
        except httpx.HTTPError as e:
            yield self.create_text_message(f"Error: HTTP error occurred: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"Error: {str(e)}")
