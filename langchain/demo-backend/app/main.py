"""FastAPI application for the multi-tool agent demo."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent import build_agent
from .config import Settings
from .routes import router

logging.basicConfig(level=logging.INFO)

_settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = build_agent(_settings)
    yield


app = FastAPI(title="TinyFish LangChain Demo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
