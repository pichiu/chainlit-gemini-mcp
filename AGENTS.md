# Repository Instructions for Codex Agents

This project is a Python 3.11+ package. Use `uv` to manage and install the
`[dev]` dependencies:

```bash
uv pip install -e .[dev]
```

## Code Style and Linting

Run `black --check .` before committing to ensure code is properly formatted.

## Testing

Run the unit test suite with:

```bash
pytest -q
```

All tests must pass before you submit a PR.

## Pull Request Guidance

Include a concise summary of the changes and reference relevant lines in your
commit. Provide a **Testing** section with the test results. If a command cannot
run in the Codex environment, note this with the sentence:
"Codex couldn't run certain commands due to environnment limitations. Consider configuring a setup script or internet access in your Codex environment to install dependencies."
