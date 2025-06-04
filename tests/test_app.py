import sys
import types
import importlib
import json
import asyncio
import pytest

# Fixture to create stub modules and import app
@pytest.fixture()
def app_module(monkeypatch):
    import os
    root = os.path.dirname(os.path.dirname(__file__))
    monkeypatch.syspath_prepend(root)
    chainlit_stub = types.ModuleType('chainlit')

    # simple decorators
    chainlit_stub.step = lambda *args, **kwargs: (lambda f: f)
    chainlit_stub.on_mcp_connect = lambda f: f
    chainlit_stub.on_chat_start = lambda f: f
    chainlit_stub.on_message = lambda f: f

    class UserSession(dict):
        def set(self, key, value):
            self[key] = value
    chainlit_stub.user_session = UserSession()

    chainlit_stub.context = types.SimpleNamespace(
        current_step=types.SimpleNamespace(name=None, output=None),
        session=types.SimpleNamespace(mcp_sessions={})
    )

    class Message:
        def __init__(self, content):
            self.content = content
        async def send(self):
            pass
    chainlit_stub.Message = Message

    monkeypatch.setitem(sys.modules, 'chainlit', chainlit_stub)

    mcp_stub = types.ModuleType('mcp')
    class ClientSession:
        pass
    mcp_stub.ClientSession = ClientSession
    monkeypatch.setitem(sys.modules, 'mcp', mcp_stub)

    genai_stub = types.ModuleType('google.genai')

    class DummyClient:
        def __init__(self, api_key=None):
            self.aio = types.SimpleNamespace(models=types.SimpleNamespace(generate_content=None))
    genai_stub.Client = DummyClient

    genai_stub.types = types.SimpleNamespace(
        FunctionDeclaration=lambda **kw: types.SimpleNamespace(**kw),
        Tool=lambda **kw: types.SimpleNamespace(**kw),
        Content=lambda **kw: types.SimpleNamespace(**kw),
        Part=lambda **kw: types.SimpleNamespace(**kw),
        GenerateContentConfig=lambda **kw: types.SimpleNamespace(**kw)
    )

    google_pkg = types.ModuleType('google')
    google_pkg.genai = genai_stub
    monkeypatch.setitem(sys.modules, 'google', google_pkg)
    monkeypatch.setitem(sys.modules, 'google.genai', genai_stub)

    dotenv_stub = types.ModuleType('dotenv')
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, 'dotenv', dotenv_stub)

    if 'app' in sys.modules:
        del sys.modules['app']
    app = importlib.import_module('app')
    return app, chainlit_stub


def test_call_tool_not_found(app_module):
    app, cl = app_module
    cl.user_session.set('mcp_tools', {})
    cl.context.current_step = types.SimpleNamespace(name=None, output=None)

    result = asyncio.run(app.call_tool(types.SimpleNamespace(name='foo', input={})))
    data = json.loads(result)
    assert 'Tool foo not found' in data['error']


def test_call_tool_success(app_module):
    app, cl = app_module
    cl.user_session.set('mcp_tools', {'c1': [{'name': 'foo', 'description': '', 'input_schema': {}}]})

    class DummySession:
        async def call_tool(self, name, input):
            return '{"ok": true}'
    cl.context.session.mcp_sessions = {'c1': (DummySession(), None)}
    cl.context.current_step = types.SimpleNamespace(name=None, output=None)

    result = asyncio.run(app.call_tool(types.SimpleNamespace(name='foo', input={'a':1})))
    assert result == '{"ok": true}'
    assert cl.context.current_step.name == 'foo'


def test_call_gemini(app_module):
    app, cl = app_module
    cl.user_session.set('mcp_tools', {'c1': [{'name': 'foo', 'description': 'd', 'input_schema': {}}]})
    cl.user_session.set('regular_tools', [{'name': 'bar', 'description': 'bd', 'input_schema': {}}])

    captured = {}
    async def fake_generate_content(model, contents, config):
        captured['model'] = model
        captured['contents'] = contents
        captured['config'] = config
        return types.SimpleNamespace(candidates=[
            types.SimpleNamespace(content=types.SimpleNamespace(parts=[types.SimpleNamespace(text='answer')]))
        ])
    app.client.aio.models.generate_content = fake_generate_content

    output = asyncio.run(app.call_gemini([{'role': 'user', 'parts': ['hi']}]))
    assert output == 'answer'
    assert captured['model'] == app.MODEL_NAME
    assert captured['contents'][0].role == 'user'
    assert captured['contents'][0].parts[0].text == 'hi'
