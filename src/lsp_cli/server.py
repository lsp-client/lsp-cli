from pathlib import Path

import httpx
import typer

from lsp_cli.manager import ManagedClientInfo, connect_manager

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


def get_manager_client() -> httpx.Client:
    return connect_manager()


@app.command("list")
def list_servers():
    """List all currently running and managed LSP servers."""
    with get_manager_client() as client:
        response = client.get("/list")
        response.raise_for_status()
        servers = [ManagedClientInfo.model_validate(s) for s in response.json()]
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
    with get_manager_client() as client:
        response = client.post("/create", json={"path": str(path.absolute())})
        response.raise_for_status()
        data = response.json()
        info = ManagedClientInfo.model_validate(data["info"])
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
        response = client.request(
            "DELETE", "/delete", json={"path": str(path.absolute())}
        )
        response.raise_for_status()
        print(f"Success: Stopped server for {path.absolute()}")


if __name__ == "__main__":
    app()
