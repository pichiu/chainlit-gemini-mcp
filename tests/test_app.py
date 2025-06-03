import pytest
import asyncio # For async function testing if needed directly
from unittest.mock import MagicMock, AsyncMock, patch

# Import functions and classes from app.py
# Assuming app.py is in the parent directory relative to the tests directory
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import flatten, show_linear_ticket, on_chat_start, regular_tools as app_regular_tools # Import regular_tools

def test_flatten():
    assert flatten([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]
    assert flatten([]) == []
    assert flatten([[], [1], [], [2, 3]]) == [1, 2, 3]

@pytest.mark.asyncio
async def test_show_linear_ticket_props():
    # Mock Chainlit elements and cl.Message
    MockCustomElement = MagicMock()
    MockMessageInstance = AsyncMock() # Instance of cl.Message
    MockMessageClass = MagicMock(return_value=MockMessageInstance) # cl.Message class

    with patch('app.cl.CustomElement', MockCustomElement):
        with patch('app.cl.Message', MockMessageClass): # Patch the class
            title = "Test Ticket"
            status = "Open"
            assignee = "Test User"
            deadline = "2024-12-31"
            tags = ["bug", "ui"]

            result = await show_linear_ticket(title, status, assignee, deadline, tags)

            expected_props = {
                "title": title,
                "status": status,
                "assignee": assignee,
                "deadline": deadline,
                "tags": tags
            }
            MockCustomElement.assert_called_once_with(name="LinearTicket", props=expected_props)
            MockMessageClass.assert_called_once_with(content="", elements=[MockCustomElement.return_value], author="show_linear_ticket")
            MockMessageInstance.send.assert_called_once()
            assert "the ticket was displayed to the user" in result
            assert str(expected_props) in result

@pytest.mark.asyncio
async def test_on_chat_start():
    mock_user_session_instance = MagicMock()

    # Patch cl.user_session to return our mock instance
    with patch('app.cl.user_session', mock_user_session_instance):
        await on_chat_start()

        # Check calls to cl.user_session.set()
        calls = mock_user_session_instance.set.call_args_list

        # Verify cl.user_session.set("chat_messages", []) was called
        assert any(call.args[0] == "chat_messages" and call.args[1] == [] for call in calls), \
            "Call to set 'chat_messages' not found or incorrect."

        # Verify cl.user_session.set("regular_tools", app_regular_tools) was called
        # app_regular_tools is imported from app.py
        assert any(call.args[0] == "regular_tools" and call.args[1] == app_regular_tools for call in calls), \
            "Call to set 'regular_tools' not found or incorrect."
