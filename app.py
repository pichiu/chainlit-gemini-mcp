import json
import os
from dotenv import load_dotenv

from mcp import ClientSession
import google.generativeai as genai
import chainlit as cl

load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

SYSTEM = (
    "You are a helpful assistant. You are a member of a team that uses "
    "Linear to manage their projects. Once you've diplayed a ticket, do "
    "not mention it again in your response - JUST SAY `here is the ticket information!`"
)

regular_tools = [
    {
        "name": "show_linear_ticket",
        "description": (
            "Displays a Linear ticket in the UI with its details. Use this tool after "
            "retrieving ticket information to show a visual representation of the ticket. "
            "The tool will create a card showing the ticket title, status, assignee, "
            "deadline, and tags. This provides a cleaner presentation than text-only responses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "status": {"type": "string"},
                "assignee": {"type": "string"},
                "deadline": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "status", "assignee", "deadline", "tags"],
        },
    }
]

# Helper to display a Linear ticket using Chainlit custom element
async def show_linear_ticket(title, status, assignee, deadline, tags):
    props = {
        "title": title,
        "status": status,
        "assignee": assignee,
        "deadline": deadline,
        "tags": tags,
    }
    ticket_element = cl.CustomElement(name="LinearTicket", props=props)
    await cl.Message(content="", elements=[ticket_element], author="show_linear_ticket").send()
    return "the ticket was displayed to the user: " + str(props)


def flatten(xss):
    return [x for xs in xss for x in xs]


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


# Initialize Gemini model
model = genai.AsyncGenerativeModel(model_name="gemini-2.5-flash-preview-05-20")


async def call_gemini(chat_messages):
    mcp_tools = cl.user_session.get("mcp_tools", {})
    regular = cl.user_session.get("regular_tools", [])
    tools = flatten([tools for _, tools in mcp_tools.items()]) + regular
    response = await model.generate_content(chat_messages, system_instruction=SYSTEM, tools=tools)
    return response.text


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

