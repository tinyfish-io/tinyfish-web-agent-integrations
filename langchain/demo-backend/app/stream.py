"""Bridge between LangGraph agent streaming and SSE events."""

import json
import logging
import time
from typing import Any, AsyncGenerator

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

logger = logging.getLogger(__name__)

# ANSI colors for terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _truncate(text: str, max_len: int = 200) -> str:
    """Truncate text for log display."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... ({len(text)} chars)"


async def stream_agent_events(
    agent: Any, user_message: str
) -> AsyncGenerator[dict, None]:
    """Consume agent.astream() and yield SSE-formatted event dicts.

    Uses triple stream mode ["updates", "messages", "custom"]:
    - "updates" gives node-level events (tool calls, tool results, final answer)
    - "messages" gives token-by-token streaming of LLM output
    - "custom" gives tool-emitted progress events (streaming_url, progress)
    """
    start = time.monotonic()
    step = 0

    print(f"\n{'='*60}")
    print(f"{BOLD}{CYAN}  NEW CHAT REQUEST{RESET}")
    print(f"{DIM}  Message: {_truncate(user_message, 100)}{RESET}")
    print(f"{'='*60}")

    yield {"type": "thinking"}

    final_content = ""

    async for mode, chunk in agent.astream(
        {"messages": [{"role": "user", "content": user_message}]},
        stream_mode=["updates", "messages", "custom"],
    ):
        if mode == "updates":
            for node_name, node_data in chunk.items():
                messages = node_data.get("messages", [])
                for msg in messages:
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in msg.tool_calls:
                            step += 1
                            elapsed = time.monotonic() - start
                            try:
                                args_str = json.dumps(tc["args"], indent=2)
                            except (TypeError, ValueError):
                                args_str = str(tc["args"])
                            print(f"\n{BOLD}{YELLOW}  [{step}] TOOL CALL  @ {elapsed:.1f}s{RESET}")
                            print(f"  {YELLOW}Tool:  {tc['name']}{RESET}")
                            for line in args_str.split("\n"):
                                print(f"  {DIM}  {line}{RESET}")
                            yield {
                                "type": "tool_call",
                                "name": tc["name"],
                                "args": tc["args"],
                            }
                    elif isinstance(msg, ToolMessage):
                        content = msg.content
                        try:
                            content = json.loads(content)
                        except (json.JSONDecodeError, TypeError):
                            pass
                        elapsed = time.monotonic() - start
                        name = msg.name or "unknown"
                        preview = _truncate(
                            json.dumps(content) if isinstance(content, (dict, list)) else str(content)
                        )
                        print(f"\n{BOLD}{GREEN}  [{step}] TOOL RESULT  @ {elapsed:.1f}s{RESET}")
                        print(f"  {GREEN}Tool:  {name}{RESET}")
                        print(f"  {DIM}  {preview}{RESET}")
                        yield {
                            "type": "tool_result",
                            "name": name,
                            "content": content,
                        }
                    elif isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                        final_content = msg.content

        elif mode == "messages":
            if not isinstance(chunk, (list, tuple)) or len(chunk) < 2:
                continue
            msg_chunk, _metadata = chunk
            if (
                isinstance(msg_chunk, AIMessageChunk)
                and msg_chunk.content
                and not msg_chunk.tool_call_chunks
            ):
                yield {"type": "token", "content": msg_chunk.content}

        elif mode == "custom":
            if isinstance(chunk, dict):
                event_type = chunk.get("type", "custom")
                try:
                    preview = _truncate(json.dumps(chunk), 120)
                except (TypeError, ValueError):
                    preview = _truncate(str(chunk), 120)
            else:
                event_type = "custom"
                preview = _truncate(str(chunk), 120)
            print(f"  {MAGENTA}  ~ {event_type}: {preview}{RESET}")
            yield chunk

    elapsed = time.monotonic() - start
    print(f"\n{'─'*60}")
    print(f"{BOLD}{GREEN}  DONE  {RESET}{DIM}{step} tool call(s) in {elapsed:.1f}s{RESET}")
    print(f"{DIM}  Response: {_truncate(final_content, 150)}{RESET}")
    print(f"{'─'*60}\n")
    yield {"type": "done", "content": final_content}
