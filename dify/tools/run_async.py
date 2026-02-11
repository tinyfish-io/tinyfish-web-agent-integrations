from collections.abc import Generator
from typing import Any

import httpx
from dify_plugin.entities.tool import ToolInvokeMessage

from dify_plugin import Tool

from tools.base import TinyfishMixin


class RunAsyncTool(TinyfishMixin, Tool):
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
                "POST", "/v1/automation/run-async", json=payload
            )

            result = response.json()
            run_id = result.get("run_id")
            error = result.get("error")

            if error:
                error_message = (
                    error.get("message", "Unknown error")
                    if isinstance(error, dict)
                    else str(error)
                )
                yield self.create_text_message(f"Failed to create run: {error_message}")
            else:
                yield self.create_text_message("Automation run created successfully!")
                yield self.create_text_message(f"Run ID: {run_id}")
                yield self.create_text_message(
                    "Use the 'get_run' tool with this run_id to check the status and retrieve results."
                )
                yield self.create_json_message({"run_id": run_id})

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                yield self.create_text_message("Error: Invalid API key")
            else:
                yield self.create_text_message(
                    f"Error: API request failed with status {e.response.status_code}: {e.response.text}"
                )
        except httpx.TimeoutException:
            yield self.create_text_message("Error: Request timed out")
        except httpx.HTTPError as e:
            yield self.create_text_message(f"Error: HTTP error occurred: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"Error: {str(e)}")
