from collections.abc import Generator
from typing import Any

import httpx
from dify_plugin.entities.tool import ToolInvokeMessage

from dify_plugin import Tool

from tools.base import TinyfishMixin


class GetRunTool(TinyfishMixin, Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        run_id = tool_parameters.get("run_id")

        if not run_id:
            yield self.create_text_message("Error: run_id is required")
            return

        try:
            response = self._tf_request("GET", f"/v1/runs/{run_id}")

            result = response.json()
            status = result.get("status")

            yield self.create_text_message(f"Run Status: {status}")
            yield self.create_text_message(f"Run ID: {result.get('run_id')}")
            yield self.create_text_message(f"Goal: {result.get('goal', 'N/A')}")

            if result.get("created_at"):
                yield self.create_text_message(f"Created: {result['created_at']}")
            if result.get("started_at"):
                yield self.create_text_message(f"Started: {result['started_at']}")
            if result.get("finished_at"):
                yield self.create_text_message(f"Finished: {result['finished_at']}")

            if result.get("streaming_url"):
                yield self.create_text_message(f"Watch live: {result['streaming_url']}")

            if status == "COMPLETED":
                yield self.create_text_message("Automation completed successfully!")
                if result.get("result"):
                    yield self.create_json_message(result["result"])
                else:
                    yield self.create_text_message("No result data available")
            elif status == "FAILED":
                error_info = result.get("error", {})
                if error_info:
                    error_message = (
                        error_info.get("message", "Unknown error")
                        if isinstance(error_info, dict)
                        else str(error_info)
                    )
                    yield self.create_text_message(
                        f"Automation failed: {error_message}"
                    )
            elif status == "RUNNING":
                yield self.create_text_message("Automation is still running...")
            elif status == "PENDING":
                yield self.create_text_message("Automation is pending...")
            elif status == "CANCELLED":
                yield self.create_text_message("Automation was cancelled")

            yield self.create_json_message(result)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                yield self.create_text_message("Error: Invalid API key")
            elif e.response.status_code == 404:
                yield self.create_text_message(
                    f"Error: Run not found with ID: {run_id}"
                )
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
