from pathlib import Path

import httpx
import typer
from rich.console import Console

from lsp_cli.manager import ManagedClientInfo, connect_manager

app = typer.Typer(
    name="server",
    help="Manage background LSP server processes.",
    add_completion=False,
    rich_markup_mode=None,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


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
        if response.status_code == 200:
            servers = [ManagedClientInfo.model_validate(s) for s in response.json()]
            if not servers:
                console.print("No servers running.")
                return
            console.print(ManagedClientInfo.format(servers))
        else:
            console.print(f"[red]Error listing servers: {response.text}[/red]")


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
        if response.status_code == 201:
            data = response.json()
            info = ManagedClientInfo.model_validate(data["info"])
            console.print(f"[green]Started server for {path.absolute()}[/green]")
            console.print(ManagedClientInfo.format(info))
        else:
            console.print(f"[red]Error starting server: {response.text}[/red]")


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
        if response.status_code == 204 or response.status_code == 200:
            console.print(f"[green]Stopped server for {path.absolute()}[/green]")
        else:
            console.print(f"[red]Error stopping server: {response.text}[/red]")


if __name__ == "__main__":
    app()
