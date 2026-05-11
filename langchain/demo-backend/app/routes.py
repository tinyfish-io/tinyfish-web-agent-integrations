"""API routes."""

import json
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .stream import stream_agent_events

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/api/chat")
async def chat(request: Request, body: ChatRequest):
    logger.info("\033[96m>> POST /api/chat — %s\033[0m", body.message[:80])
    agent = request.app.state.agent

    async def event_generator():
        try:
            async for event in stream_agent_events(agent, body.message):
                if await request.is_disconnected():
                    logger.info("\033[93m   Client disconnected\033[0m")
                    break
                yield {"data": json.dumps(event)}
        except Exception as e:
            logger.exception("\033[91m   Error during chat streaming: %s\033[0m", e)
            yield {"data": json.dumps({"type": "error", "message": "An internal error occurred"})}

    return EventSourceResponse(event_generator(), ping=15)
