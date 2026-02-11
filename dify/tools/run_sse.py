import json
from collections.abc import Generator
from typing import Any

import httpx
from dify_plugin.entities.tool import ToolInvokeMessage

from dify_plugin import Tool

from tools.base import TinyfishMixin
from tools.constants import API_BASE_URL


class RunSseTool(TinyfishMixin, Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        if not tool_parameters.get("url"):
            yield self.create_text_message("Error: URL is required")
            return

        if not tool_parameters.get("goal"):
            yield self.create_text_message("Error: Goal is required")
            return

        payload = self._build_automation_payload(tool_parameters)

        try:
            with httpx.Client(timeout=300.0) as client:
                with client.stream(
                    "POST",
                    f"{API_BASE_URL}/v1/automation/run-sse",
                    headers=self._api_headers,
                    json=payload,
                ) as response:
                    if response.status_code == 401:
                        yield self.create_text_message("Error: Invalid API key")
                        return
                    elif response.status_code >= 400:
                        response.read()
                        yield self.create_text_message(
                            f"Error: API request failed with status {response.status_code}: {response.text}"
                        )
                        return

                    final_result = None

                    for line in response.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue

                        try:
                            event_data = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue

                        event_type = event_data.get("type")

                        if event_type == "STARTED":
                            yield self.create_text_message(
                                f"Automation started (Run ID: {event_data.get('runId')})"
                            )
                        elif event_type == "STREAMING_URL":
                            streaming_url = event_data.get("streamingUrl")
                            if streaming_url:
                                yield self.create_text_message(
                                    f"Watch live: {streaming_url}"
                                )
                        elif event_type == "PROGRESS":
                            yield self.create_text_message(
                                event_data.get("purpose", "Processing...")
                            )
                        elif event_type == "COMPLETE":
                            status = event_data.get("status")
                            final_result = event_data.get("resultJson")

                            if status == "COMPLETED":
                                yield self.create_text_message(
                                    "Automation completed successfully!"
                                )
                                if final_result:
                                    yield self.create_json_message(final_result)
                                else:
                                    yield self.create_text_message(
                                        "No result data returned"
                                    )
                            else:
                                yield self.create_text_message(
                                    f"Automation failed: {event_data.get('error', 'Unknown error')}"
                                )

                    if final_result is None:
                        yield self.create_text_message(
                            "Automation ended without returning a result"
                        )

        except httpx.TimeoutException:
            yield self.create_text_message(
                "Error: Request timed out. The automation may be taking too long."
            )
        except httpx.HTTPError as e:
            yield self.create_text_message(f"Error: HTTP error occurred: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"Error: {str(e)}")
