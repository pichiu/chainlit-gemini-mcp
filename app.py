import json

from mcp import ClientSession
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

import chainlit as cl

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini client
# Ensure GOOGLE_API_KEY is loaded by load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

SYSTEM = "You are a helpful assistant. You are a member of a team that uses Linear to manage their projects. Once you've diplayed a ticket, do not mention it again in your response - JUST SAY `here is the ticket information!`"

gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-preview-0514",
    system_instruction=SYSTEM,
)

regular_tools = [{
    "name": "show_linear_ticket",
    "description": "Displays a Linear ticket in the UI with its details. Use this tool after retrieving ticket information to show a visual representation of the ticket. The tool will create a card showing the ticket title, status, assignee, deadline, and tags. This provides a cleaner presentation than text-only responses.",
    "input_schema": {
        "type": "object",
        "properties": {"title": {"type": "string"}, "status": {"type": "string"}, "assignee": {"type": "string"}, "deadline": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}},
        "required": ["title", "status", "assignee", "deadline", "tags"]
    }
}]

async def show_linear_ticket(title, status, assignee, deadline, tags):
    props = {
        "title": title,
        "status": status,
        "assignee": assignee,
        "deadline": deadline,
        "tags": tags
    }
    print("props", props)
    ticket_element = cl.CustomElement(name="LinearTicket", props=props)
    await cl.Message(content="", elements=[ticket_element], author="show_linear_ticket").send()
    return "the ticket was displayed to the user: " + str(props)


def flatten(xss):
    return [x for xs in xss for x in xs]

@cl.on_mcp_connect
async def on_mcp(connection, session: ClientSession):
    result = await session.list_tools()
    tools = [{
        "name": t.name,
        "description": t.description,
        "input_schema": t.inputSchema,
        } for t in result.tools]

    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools[connection.name] = tools
    cl.user_session.set("mcp_tools", mcp_tools)


@cl.step(type="tool")
async def call_tool(tool_use):
    tool_name = tool_use.name
    tool_input = tool_use.input

    current_step = cl.context.current_step
    current_step.name = tool_name

    # Identify which mcp is used
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

async def call_gemini(chat_messages, current_cl_message_ui: cl.Message):
    mcp_tools_list = cl.user_session.get("mcp_tools", {})
    all_tools_definitions = flatten([tools for _, tools in mcp_tools_list.items()]) + cl.user_session.get("regular_tools", [])

    gemini_tools_for_api = []
    for tool_def in all_tools_definitions:
        gemini_tools_for_api.append(genai.types.FunctionDeclaration(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=tool_def["input_schema"]
        ))

    gemini_chat_history = []
    for message in chat_messages:
        role = "model" if message["role"] == "assistant" else message["role"]
        content = message["content"]
        parts = []
        is_special_content = False

        if isinstance(content, str):
            try:
                data = json.loads(content)
                if isinstance(data, dict) and data.get("type") == "tool_result":
                    parts.append(genai.types.Part(
                        function_response=genai.types.FunctionResponse(
                            name=data["tool_name"],
                            response={"content": data["tool_result"]}
                        )
                    ))
                    is_special_content = True
                elif isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("type") == "function_call":
                    if role == "model": # 'assistant' is mapped to 'model'
                         for fc_data in data:
                              parts.append(genai.types.Part(function_call=genai.types.FunctionCall(name=fc_data["name"], args=fc_data["args"])))
                         is_special_content = True
                    # else: user role with this structure, treat as text below
            except (json.JSONDecodeError, TypeError):
                pass # Not a special JSON string, will be treated as plain text

        if not is_special_content:
            parts.append(genai.types.Part(text=str(content)))

        if parts: # Only add if parts were generated
            gemini_chat_history.append({"role": role, "parts": parts})

    response_stream = await gemini_model.generate_content_async(
        gemini_chat_history,
        tools=gemini_tools_for_api,
        stream=True,
        # safety_settings={ # Optional
        #     HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        # }
    )

    full_response_content_parts = []
    final_response_obj = None

    async for chunk in response_stream:
        if chunk.text:
            await current_cl_message_ui.stream_token(chunk.text)
        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
             full_response_content_parts.extend(chunk.candidates[0].content.parts)
        final_response_obj = chunk

    if current_cl_message_ui.content or not full_response_content_parts:
        # If text was streamed or if there are no parts (e.g. error, empty response)
        # ensure message is sent if it has content, or if it's meant to be an empty container.
        if not current_cl_message_ui.streaming: # Avoid sending if it's already auto-sent by stream_token completion
             await current_cl_message_ui.send()

    return final_response_obj, full_response_content_parts

@cl.on_chat_start
async def start_chat():
    cl.user_session.set("chat_messages", [])
    cl.user_session.set("regular_tools", regular_tools)

@cl.on_message
async def on_message(msg: cl.Message):
    chat_messages = cl.user_session.get("chat_messages")
    chat_messages.append({"role": "user", "content": msg.content})

    # Parent UI message for the entire turn, including potential tool calls
    turn_ui_parent_message = msg # Use the user's message as the root for this turn's UI elements

    max_tool_iterations = 5
    current_iteration = 0

    while current_iteration < max_tool_iterations:
        current_iteration += 1

        # UI message for the current LLM response stream
        llm_response_ui_message = cl.Message(content="", parent_id=turn_ui_parent_message.id if turn_ui_parent_message else None)

        gemini_response_obj, full_response_parts = await call_gemini(chat_messages, llm_response_ui_message)

        text_response_for_history = "".join([p.text for p in full_response_parts if p.text])
        active_function_calls = [p.function_call for p in full_response_parts if p.function_call and p.function_call.name]

        assistant_turn_content_for_history = []
        if text_response_for_history:
            assistant_turn_content_for_history.append(text_response_for_history)

        if active_function_calls:
            # This specific format is for our `call_gemini` to parse when role is "model"
            assistant_turn_content_for_history.append(
                json.dumps([{"type": "function_call", "name": fc.name, "args": dict(fc.args)} for fc in active_function_calls])
            )

        if assistant_turn_content_for_history:
             # Combine text and FC info for history. If only FC, it's just the FC JSON string. If both, space separated.
            chat_messages.append({"role": "assistant", "content": " ".join(assistant_turn_content_for_history)})
        elif not gemini_response_obj or not gemini_response_obj.candidates: # Handle empty/blocked responses
            empty_msg = "Model returned no content."
            if gemini_response_obj and gemini_response_obj.prompt_feedback and gemini_response_obj.prompt_feedback.block_reason:
                empty_msg = f"Model blocked: {gemini_response_obj.prompt_feedback.block_reason_message or gemini_response_obj.prompt_feedback.block_reason}"

            # Ensure the empty/error message is displayed if not already through llm_response_ui_message
            if not llm_response_ui_message.content:
                 await cl.Message(content=empty_msg, parent_id=turn_ui_parent_message.id if turn_ui_parent_message else None).send()

            chat_messages.append({"role": "assistant", "content": empty_msg})
            break # Exit tool loop due to empty/blocked response


        if not active_function_calls:
            # No function calls, this is the end of the turn.
            # Text was already streamed to llm_response_ui_message.
            # If llm_response_ui_message was empty but text_response_for_history is not (e.g. streaming failed but got content)
            if not llm_response_ui_message.content and text_response_for_history:
                 await cl.Message(content=text_response_for_history, parent_id=turn_ui_parent_message.id if turn_ui_parent_message else None).send()
            break # Exit loop, no more tools to call

        # If there are function calls, process them
        tool_results_added_this_iteration = False
        for function_call in active_function_calls:
            tool_name = function_call.name
            tool_args = dict(function_call.args)

            # Announce tool call (cl.step in call_tool will also do this for MCP tools)
            # For show_linear_ticket, we manage UI explicitly.
            tool_ui_parent_id = llm_response_ui_message.id # Nest under the LLM message that requested it

            # No need for explicit "Calling tool..." if the tool itself creates UI steps.
            # tool_call_announcement_msg = cl.Message(content=f"Executing tool: `{tool_name}`", type="system", parent_id=tool_ui_parent_id)
            # await tool_call_announcement_msg.send()

            if tool_name == "show_linear_ticket":
                # show_linear_ticket creates its own message. We can pass parent_id.
                # For CustomElement, it's better if it's a new message not child of LLM text.
                # Let's make it a sibling to the user message, or child of the main turn message
                cl.context.current_step.parent_id = turn_ui_parent_message.id # So tool UI is clean
                tool_result_content = await show_linear_ticket(**tool_args)
            else:
                # call_tool is a @cl.step, it will create its own UI elements.
                # Ensure its parent is set correctly for nesting if desired.
                cl.context.current_step.parent_id = turn_ui_parent_message.id
                mock_tool_use = type('ToolUse', (), {'name': tool_name, 'input': tool_args})()
                tool_result_content = await call_tool(mock_tool_use)

            # await tool_call_announcement_msg.remove() # Clean up announcement

            chat_messages.append({
                "role": "user", # This message contains the tool result
                "content": json.dumps({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "tool_result": str(tool_result_content)
                })
            })
            tool_results_added_this_iteration = True

        if not tool_results_added_this_iteration:
            # Should not happen if active_function_calls is not empty
            break

    if current_iteration == max_tool_iterations and active_function_calls:
        await cl.Message(content="Max tool iterations reached.", parent_id=turn_ui_parent_message.id if turn_ui_parent_message else None).send()

    # cl.user_session.set("chat_messages", chat_messages) # Not needed, list is modified in place
