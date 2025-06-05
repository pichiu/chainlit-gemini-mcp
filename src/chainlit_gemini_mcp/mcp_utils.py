from __future__ import annotations

from typing import Any, Dict, Iterable

import chainlit as cl
from mcp import ClientSession


async def store_tools(connection, session: ClientSession) -> None:
    """Store tools discovered on a new MCP connection."""
    result = await session.list_tools()
    tools = [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema,
        }
        for t in result.tools
    ]
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools[connection.name] = tools
    cl.user_session.set("mcp_tools", mcp_tools)


async def remove_tools(name: str) -> None:
    """Remove tools when an MCP connection is closed."""
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools.pop(name, None)
    cl.user_session.set("mcp_tools", mcp_tools)


def find_mcp_for_tool(tool_name: str, mcp_tools: Dict[str, Iterable[Dict[str, Any]]]):
    """Return the MCP connection name that exposes ``tool_name``."""
    for name, tools in mcp_tools.items():
        for tool in tools:
            if tool.get("name") == tool_name:
                return name
    return None


async def call_mcp_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    mcp_tools: Dict[str, Iterable[Dict[str, Any]]],
    mcp_sessions: Dict[str, ClientSession],
) -> Any:
    """Call a tool on the appropriate MCP connection."""
    name = find_mcp_for_tool(tool_name, mcp_tools)
    if not name:
        raise ValueError(f"Tool '{tool_name}' not found")

    session = mcp_sessions[name]
    result = await session.call_tool(tool_name, tool_input)
    return getattr(result, "output", result)
