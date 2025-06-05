# chainlit-gemini-mcp

This project demonstrates how to use **Chainlit** with the Google
**Gemini** SDK to call tools exposed through an MCP server.

## Development

Create a virtual environment and install the dependencies using
[uv](https://github.com/astral-sh/uv):

```bash
uv pip install -e .[dev]
```

Run the tests with `pytest`:

```bash
pytest
```

Start the Chainlit application:

```bash
chainlit run src/chainlit_gemini_mcp/app.py
```

Make sure to set the `GOOGLE_API_KEY` environment variable so that the
Gemini client can authenticate.

## Logging

The application uses Python's `logging` module. Set the `LOGLEVEL`
environment variable to `DEBUG` to see verbose output when starting the
app:

```bash
LOGLEVEL=DEBUG chainlit run src/chainlit_gemini_mcp/app.py
```
