from collections.abc import Generator
from typing import Any

import httpx
from dify_plugin.entities.tool import ToolInvokeMessage

from dify_plugin import Tool

from tools.base import TinyfishMixin


class ListRunsTool(TinyfishMixin, Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        status = tool_parameters.get("status")
        limit = tool_parameters.get("limit", 20)
        cursor = tool_parameters.get("cursor")

        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if limit:
            params["limit"] = int(limit)
        if cursor:
            params["cursor"] = cursor

        try:
            response = self._tf_request("GET", "/v1/runs", params=params)

            result = response.json()
            data = result.get("data", [])
            pagination = result.get("pagination", {})

            if not data:
                yield self.create_text_message("No runs found")
                return

            yield self.create_text_message(f"Found {len(data)} run(s)")

            if pagination.get("has_more"):
                yield self.create_text_message(
                    f"More results available. Use cursor: {pagination.get('next_cursor')}"
                )

            for idx, run in enumerate(data, 1):
                yield self.create_text_message(
                    f"\n{idx}. {run.get('status')}"
                    f"\n   Run ID: {run.get('run_id')}"
                    f"\n   Goal: {run.get('goal', 'N/A')}"
                    f"\n   Created: {run.get('created_at', 'N/A')}"
                )

            yield self.create_json_message(result)

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
