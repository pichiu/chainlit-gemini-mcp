import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.abspath("src"))

from chainlit_gemini_mcp.gemini_client import get_client
from chainlit_gemini_mcp.mcp_utils import find_mcp_for_tool, call_mcp_tool


class DummySession:
    def __init__(self):
        self.called = None

    class Result:
        def __init__(self, output: str):
            self.output = output

    async def call_tool(self, name, arguments=None, **_):
        self.called = (name, arguments)
        return self.Result(f"ok:{arguments['location']}")


def test_call_mcp_tool():
    mcp_tools = {"conn": [{"name": "get_current_weather"}]}
    session = DummySession()
    result = asyncio.run(
        call_mcp_tool(
            "get_current_weather",
            {"location": "paris"},
            mcp_tools,
            {"conn": session},
        )
    )
    assert result == "ok:paris"
    assert session.called == ("get_current_weather", {"location": "paris"})


def test_call_mcp_tool_missing():
    with pytest.raises(ValueError):
        asyncio.run(
            call_mcp_tool(
                "get_current_weather",
                {"location": "lyon"},
                {},
                {},
            )
        )


def test_find_mcp_for_tool():
    tools = {"c1": [{"name": "foo"}], "c2": [{"name": "bar"}]}
    assert find_mcp_for_tool("bar", tools) == "c2"
    assert find_mcp_for_tool("missing", tools) is None


def test_get_client(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "key")
    client = get_client()
    assert hasattr(client, "models")
