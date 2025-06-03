# Chainlit Gemini MCP Application

## Description

This is a Chainlit application that leverages Google's Gemini API (specifically the `gemini-1.5-flash-preview-0514` model) for advanced conversational AI capabilities. The application also demonstrates integration with Multi-Channel Platform (MCP) tools, allowing it to extend its functionality by interacting with external services. An example of such an MCP tool could be `uvx mcp-google-sheets@latest`, enabling interactions with Google Sheets.

## Features

*   **Conversational AI:** Utilizes Google's Gemini 1.5 Flash model for fluid and context-aware conversations.
*   **Streaming Responses:** Provides real-time streaming of responses from the Gemini API for an interactive user experience.
*   **Tool Integration (Function Calling):** Supports integration with custom tools and MCP tools via Gemini's function calling capabilities.
*   **MCP Ready:** Designed to connect to MCP servers to access a wider range of tools and data sources.
*   **Easy Setup:** Uses `uv` for fast dependency management and environment setup.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python:** Version 3.9 or higher (as specified in `pyproject.toml`).
*   **`uv`:** A fast Python package installer and resolver. Installation instructions can be found here: [astral-sh/uv](https://github.com/astral-sh/uv).
*   **Google API Key:** A valid Google Cloud API key with the Gemini API (Generative Language API) enabled.

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/chainlit-gemini-mcp.git
    ```

2.  **Navigate to the project directory:**
    ```bash
    cd chainlit-gemini-mcp
    ```

3.  **Create a virtual environment using `uv`:**
    This command creates a virtual environment in a `.venv` directory in your project.
    ```bash
    uv venv
    ```

4.  **Activate the virtual environment:**
    *   On macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```
    *   On Windows:
        ```bash
        .venv\Scripts\activate
        ```

5.  **Install dependencies using `uv`:**
    This command installs the dependencies specified in the `pyproject.toml` file.
    ```bash
    uv sync
    ```

6.  **Create a `.env` file:**
    This file will store your Google API key. You can create it manually.
    For example, on Linux or macOS:
    ```bash
    touch .env
    ```
    Then, open the `.env` file and add your Google API key in the following format:

7.  **Add your Google API key to the `.env` file:**
    Open the `.env` file and add your key:
    ```env
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    ```
    Replace `"YOUR_GOOGLE_API_KEY"` with your actual API key.

## Running the Application

Once the setup is complete and the virtual environment is activated, you can run the Chainlit application:

```bash
chainlit run app.py -w
```

The `-w` flag enables auto-reloading, so the application will automatically update if you make changes to the code. Open your web browser and navigate to the URL provided by Chainlit (usually `http://localhost:8000`).

## MCP Server Integration

This application is configured in `app.py` to connect to and utilize tools from Multi-Channel Platform (MCP) servers. While the core `app.py` handles the logic for invoking MCP tools surfaced by the Gemini model, the actual connection and configuration of which MCP servers Chainlit connects to is typically managed outside `app.py`.

This might involve:
*   Chainlit configuration files (e.g., in a `.chainlit/config.toml` file).
*   Environment variables that Chainlit reads to discover and connect to MCP instances.

An example of an MCP tool that could be used with this application is `uvx mcp-google-sheets@latest`, which would allow the Chainlit app to interact with Google Sheets through natural language commands processed by Gemini. Ensure your Chainlit environment is configured to connect to any necessary MCP servers for full functionality.
