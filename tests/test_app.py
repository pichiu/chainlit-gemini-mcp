import os
import sys
import logging
import pytest

os.environ.setdefault("GOOGLE_API_KEY", "key")

sys.path.insert(0, os.path.abspath("src"))

import asyncio
import chainlit as cl
from chainlit_gemini_mcp import app


class DummyResponse:
    def __init__(self, text: str):
        self.text = text


class DummyMessage:
    def __init__(self, content: str):
        self.content = content


class DummyCLMessage:
    def __init__(self, *, content: str):
        self.content = content

    async def send(self):
        DummyCLMessage.sent = self.content


async def fake_generate_content(**_):
    return DummyResponse("hello")


def test_on_message_logs_response(monkeypatch, caplog):
    monkeypatch.setattr(
        app.client.aio.models, "generate_content", fake_generate_content
    )
    monkeypatch.setattr(cl, "Message", DummyCLMessage)

    with caplog.at_level(logging.DEBUG):
        asyncio.run(app.on_message(DummyMessage("hi")))

    assert DummyCLMessage.sent == "hello"
    assert any("hello" in record.getMessage() for record in caplog.records)
