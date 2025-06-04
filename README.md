# Chainlit Gemini MCP Example

This repository demonstrates how to run a Chainlit application powered by Google
Gemini and connected to an MCP server.

## Setup

1. Install dependencies with [uv](https://github.com/astral-sh/uv) using the
   provided `pyproject.toml` and `uv.lock`:

```bash
uv sync
```

2. Start the MCP server for Google Sheets:

```bash
uvx mcp-google-sheets@latest
```

3. Export your Google API key so the Gemini SDK can authenticate:

```bash
export GOOGLE_API_KEY=your_key
```

4. Run the Chainlit app:

```bash
chainlit run app.py -w
```

The app uses the `gemini-2.5-flash-preview-05-20` model and shows how tool calls
can be handled through MCP.
