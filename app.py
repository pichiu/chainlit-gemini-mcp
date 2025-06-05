import json
import os
import types
from dotenv import load_dotenv

from mcp import ClientSession
import google.genai as genai
import chainlit as cl

load_dotenv()

# Configure Gemini client
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else genai.Client()

SYSTEM = "You are a helpful assistant."

# No builtin tools
regular_tools = []


def flatten(xss):
    return [x for xs in xss for x in xs]


def _snake_to_camel(name: str) -> str:
    """Convert snake_case names to camelCase."""
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:]) if len(parts) > 1 else name


def normalize_schema(value):
    """Recursively convert snake_case keys to camelCase in a JSON schema."""
    # Support Pydantic objects which implement ``model_dump`` or ``dict``
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        value = value.model_dump()
    elif hasattr(value, "dict") and callable(getattr(value, "dict")):
        value = value.dict()

    # If value is a JSON string, try to parse it
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return value

    if isinstance(value, dict):
        return {
            _snake_to_camel(k): normalize_schema(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [normalize_schema(v) for v in value]
    return value


@cl.on_mcp_connect
async def on_mcp(connection, session: ClientSession):
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


@cl.step(type="tool")
async def call_tool(tool_use):
    tool_name = tool_use.name
    tool_input = tool_use.input

    current_step = cl.context.current_step
    current_step.name = tool_name

    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_name = None
    for connection_name, tools in mcp_tools.items():
        if any(tool.get("name") == tool_name for tool in tools):
            mcp_name = connection_name
            break

    if not mcp_name:
        current_step.output = json.dumps({"error": f"Tool {tool_name} not found in any MCP connection"})
        return current_step.output

    mcp_session, _ = cl.context.session.mcp_sessions.get(mcp_name)

    if not mcp_session:
        current_step.output = json.dumps({"error": f"MCP {mcp_name} not found in any MCP connection"})
        return current_step.output

    try:
        current_step.output = await mcp_session.call_tool(tool_name, tool_input)
    except Exception as e:
        current_step.output = json.dumps({"error": str(e)})

    return current_step.output


# Target model name
MODEL_NAME = "gemini-2.5-flash-preview-05-20"


async def call_gemini(chat_messages):
    mcp_tools = cl.user_session.get("mcp_tools", {})
    regular = cl.user_session.get("regular_tools", [])

    # Convert tools to FunctionDeclarations understood by google-genai
    all_tools = flatten([tools for _, tools in mcp_tools.items()]) + regular
    declarations = [
        genai.types.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=normalize_schema(t["input_schema"]),
        )
        for t in all_tools
    ]
    tool_config = (
        genai.types.Tool(function_declarations=declarations)
        if declarations
        else None
    )

    contents = [
        genai.types.Content(
            role=m["role"],
            parts=[genai.types.Part(text=p) for p in m.get("parts", [])],
        )
        for m in chat_messages
    ]

    config = genai.types.GenerateContentConfig(
        system_instruction=SYSTEM, tools=[tool_config] if tool_config else None
    )

    response = await client.aio.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=config,
    )

    candidate = response.candidates[0]

    function_calls = [
        part.function_call
        for part in getattr(candidate.content, "parts", [])
        if getattr(part, "function_call", None)
    ]

    if not function_calls:
        return "".join(part.text or "" for part in candidate.content.parts)

    response_parts = []
    for call in function_calls:
        args = call.args
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        tool_output = await call_tool(types.SimpleNamespace(name=call.name, input=args))
        response_parts.append(
            genai.types.Part.from_function_response(
                name=call.name, response={"content": tool_output}
            )
        )

    followup_contents = contents + [
        candidate.content,
        genai.types.Content(role="function", parts=response_parts),
    ]

    followup = await client.aio.models.generate_content(
        model=MODEL_NAME,
        contents=followup_contents,
        config=config,
    )

    final_candidate = followup.candidates[0]
    return "".join(part.text or "" for part in final_candidate.content.parts)


@cl.on_chat_start
async def start_chat():
    cl.user_session.set("chat_messages", [])
    cl.user_session.set("regular_tools", regular_tools)
@cl.on_message
async def on_message(msg: cl.Message):
    chat_messages = cl.user_session.get("chat_messages")
    chat_messages.append({"role": "user", "parts": [msg.content]})
    response_text = await call_gemini(chat_messages)
    await cl.Message(content=response_text).send()
    chat_messages.append({"role": "assistant", "parts": [response_text]})

