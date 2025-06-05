from __future__ import annotations
import os
import logging
import chainlit as cl

logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

from google.genai import types

from chainlit_gemini_mcp.gemini_client import get_client
from chainlit_gemini_mcp.mcp_utils import (
    call_mcp_tool,
    store_tools,
    remove_tools,
)


MODEL_NAME = "gemini-2.5-flash-preview-05-20"  # default model
client = get_client()


async def get_current_weather(location: str) -> str:
    """Delegate a weather query to an MCP tool."""
    logger.info("get_current_weather called with location=%s", location)
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_sessions = {
        name: session
        for name, (session, _) in getattr(
            cl.context.session, "mcp_sessions", {}
        ).items()
    }
    result = await call_mcp_tool(
        "get_current_weather",
        {"location": location},
        mcp_tools,
        mcp_sessions,
    )
    return str(result)


@cl.on_mcp_connect
async def on_mcp_connect(connection, session):
    await store_tools(connection, session)


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name, session):
    await remove_tools(name)


@cl.on_message
async def on_message(message: cl.Message):
    response = await client.aio.models.generate_content(
        model=MODEL_NAME,
        contents=message.content,
        config=types.GenerateContentConfig(tools=[get_current_weather]),
    )
    await cl.Message(content=response.text).send()
