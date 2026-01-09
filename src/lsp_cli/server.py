from pathlib import Path

import typer
from lsp_client.clients.lang import lang_clients

from lsp_cli.client import find_client
from lsp_cli.manager import (
    CreateClientRequest,
    CreateClientResponse,
    DeleteClientRequest,
    DeleteClientResponse,
    ManagedClientInfo,
    ManagedClientInfoList,
    connect_manager,
)
from lsp_cli.utils.http import HttpClient

app = typer.Typer(
    name="server",
    help="Manage background LSP server processes.",
    add_completion=False,
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 1000,
        "terminal_width": 1000,
    },
)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Manage LSP servers."""
    if ctx.invoked_subcommand is None:
        list_servers()


def get_manager_client() -> HttpClient:
    return connect_manager()


@app.command("list")
def list_servers():
    """List all currently running and managed LSP servers."""
    with get_manager_client() as client:
        resp = client.get("/list", ManagedClientInfoList)
        servers = resp.root if resp else []
        if not servers:
            print("No servers running.")
            return
        print(ManagedClientInfo.format(servers))


@app.command("start")
def start_server(
    path: Path = typer.Argument(
        Path.cwd(),
        help="Path to a code file or project directory to start the LSP server for.",
    ),
):
    """Start a background LSP server for the project containing the specified path."""
    # Check if the path exists
    if not path.exists():
        print(f"Error: Path does not exist: {path.absolute()}")
        raise typer.Exit(1)

    # Try to find a language client for this path
    target = find_client(path)

    if target is None:
        # No language support found - generate list of supported languages dynamically
        supported_langs = sorted(
            {
                client_cls.get_language_config().kind.value
                for client_cls in lang_clients.values()
            }
        )
        supported_langs_str = ", ".join(supported_langs)

        print(f"Error: Language not supported for path: {path.absolute()}")
        print()
        print("The CLI cannot analyze code files in this language.")
        print(f"Supported languages: {supported_langs_str}")
        print()
        print("Please check:")
        print("  - The file extension matches a supported language")
        print(
            "  - The project has the required language markers (e.g., go.mod, Cargo.toml)"
        )
        raise typer.Exit(1)

    with get_manager_client() as client:
        resp = client.post(
            "/create", CreateClientResponse, json=CreateClientRequest(path=path)
        )
        assert resp is not None
        info = resp.info
        print(f"Success: Started server for {path.absolute()}")
        print(ManagedClientInfo.format(info))


@app.command("stop")
def stop_server(
    path: Path = typer.Argument(
        Path.cwd(),
        help="Path to a code file or project directory to stop the LSP server for.",
    ),
):
    """Stop the background LSP server for the project containing the specified path."""
    with get_manager_client() as client:
        client.delete(
            "/delete", DeleteClientResponse, json=DeleteClientRequest(path=path)
        )
        print(f"Success: Stopped server for {path.absolute()}")


if __name__ == "__main__":
    app()
