# Contributing to LSP CLI

Thank you for your interest in contributing to `lsp-cli`! This project provides a powerful command-line interface for the Language Server Agent Protocol (LSAP).

## Development Setup

We use `uv` for dependency management. Please ensure you have it installed.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/lsp-client/lsp-cli.git
    cd lsp-cli
    ```

2.  **Sync dependencies**:
    ```bash
    uv sync
    ```

3.  **Run the CLI in development**:
    ```bash
    uv run lsp --help
    ```

## Development Workflow

### Code Style & Quality

We maintain high standards for code quality and type safety:

- **Formatting & Linting**: We use `ruff`.
  ```bash
  uv run ruff check --fix
  uv run ruff format
  ```
- **Type Checking**: We use `pyright` (referred to as `ty` in some local environments).
  ```bash
  uv run pyright
  ```
- **Testing**: We use `pytest`.
  ```bash
  uv run pytest
  ```

### Adding New Commands

`lsp-cli` uses `typer` for its command-line interface. Commands are defined in `src/lsp_cli/__main__.py`.

1.  Define the command using `@app.command()`.
2.  Use the `Annotated` pattern for arguments and options (see `src/lsp_cli/options.py`).
3.  Ensure the command uses the `init_client` context manager to interact with the background manager.
4.  Format the output using `rich`.

### Improving the Manager

The background manager is located in `src/lsp_cli/manager/`. It uses `litestar` to provide a UDS-based API for managing LSP clients.

### Adding New Language Servers

Support for specific language servers (like Pyright, Rust-Analyzer, etc.) is handled by the [lsp-client](https://github.com/lsp-client/python-sdk) library. If you want to add support for a new language server, please contribute to that repository instead.

## Pull Request Process

1.  Create a new branch for your feature or bugfix.
2.  Ensure all tests pass and there are no linting/type errors.
3.  Write a clear, concise commit message.
4.  Submit a pull request with a detailed description of your changes.

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.
