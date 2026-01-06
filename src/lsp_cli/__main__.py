import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

import typer
from loguru import logger
from lsap.definition import DefinitionCapability, DefinitionClient
from lsap.hover import HoverCapability, HoverClient
from lsap.outline import OutlineCapability, OutlineClient
from lsap.reference import ReferenceCapability, ReferenceClient
from lsap.search import SearchCapability, SearchClient
from lsap.symbol import SymbolCapability, SymbolClient
from lsap_schema.definition import DefinitionRequest
from lsap_schema.hover import HoverRequest
from lsap_schema.locate import LineScope, Locate, SymbolScope
from lsap_schema.models import SymbolKind
from lsap_schema.outline import OutlineRequest
from lsap_schema.reference import ReferenceRequest
from lsap_schema.search import SearchRequest
from lsap_schema.symbol import SymbolRequest
from lsp_client import Client
from rich.console import Console
from rich.markdown import Markdown

from lsp_cli.client import find_client
from lsp_cli.manager import CreateClientRequest, CreateClientResponse
from lsp_cli.manager.server import ManagerServer
from lsp_cli.server import app as server_app
from lsp_cli.server import get_manager_client
from lsp_cli.settings import settings
from lsp_cli.utils.sync import cli_syncify

from . import options as op

app = typer.Typer(
    help="LSP CLI: A command-line tool for interacting with Language Server Protocol (LSP) features.",
    add_completion=False,
    rich_markup_mode=None,
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 1000,
        "terminal_width": 1000,
    },
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=False,
)
app.add_typer(server_app, name="server")

console = Console()


@asynccontextmanager
async def init_client(path: Path) -> AsyncGenerator[Client]:
    path = path.absolute()
    if not (target := find_client(path)):
        console.print(f"[red]Error:[/red] No LSP client for {path}")
        raise typer.Exit(1)

    with get_manager_client() as httpx:
        req = CreateClientRequest(path=path).model_dump(mode="json")
        resp = httpx.post("/create", json=req)
        json = resp.raise_for_status().json()
        resp = CreateClientResponse.model_validate(json)

    async with target.client_cls(
        server=ManagerServer(uds_path=resp.uds_path),
        workspace=target.project_path,
    ).unmanaged() as client:
        yield client


def create_locate(
    file_path: Path,
    scope: str | None = None,
    find: str | None = None,
    marker: str = "<HERE>",
) -> Locate:
    parsed_scope = None
    if scope:
        if "," in scope:
            try:
                start, end = map(int, scope.split(","))
                parsed_scope = LineScope(line=(start, end))
            except ValueError:
                parsed_scope = SymbolScope(symbol_path=scope.split("."))
        elif scope.isdigit():
            parsed_scope = LineScope(line=int(scope))
        else:
            parsed_scope = SymbolScope(symbol_path=scope.split("."))

    try:
        return Locate(file_path=file_path, scope=parsed_scope, find=find, marker=marker)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def print_resp(resp, ctx: typer.Context):
    if ctx.obj and ctx.obj.get("markdown"):
        console.print(Markdown(resp.format()))
    else:
        console.print(resp.format())


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable verbose debug logging for troubleshooting.",
    ),
    markdown: op.MarkdownOpt = False,
):
    if debug:
        settings.debug = True

    logger.remove()
    logger.add(sys.stderr, level=settings.effective_log_level)

    ctx.ensure_object(dict)
    ctx.obj["markdown"] = markdown
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()


@app.command(
    "definition",
    help="Find the definition (default), declaration (--decl), or type definition (--type) of a symbol. (alias: def)",
)
@app.command("def", hidden=True)
@cli_syncify
async def get_definition(
    ctx: typer.Context,
    file_path: op.FileArg,
    scope: op.ScopeOpt = None,
    find: op.FindOpt = None,
    marker: op.MarkerOpt = "<HERE>",
    mode: Annotated[
        Literal["definition", "declaration", "type_definition"],
        typer.Option(
            "--mode",
            "-m",
            help="Search mode (default: definition).",
            hidden=True,
        ),
    ] = "definition",
    decl: bool = typer.Option(False, "--decl", help="Search for symbol declaration."),
    type_def: bool = typer.Option(False, "--type", help="Search for type definition."),
):
    if decl and type_def:
        console.print("[red]Error:[/red] --decl and --type are mutually exclusive")
        raise typer.Exit(1)

    if decl:
        mode = "declaration"
    elif type_def:
        mode = "type_definition"

    locate = create_locate(file_path, scope, find, marker)

    async with init_client(file_path) as client:
        if not isinstance(client, DefinitionClient):
            console.print("[red]Error:[/red] Client does not support definitions")
            raise typer.Exit(1)

        cap = DefinitionCapability(client)
        req = DefinitionRequest(
            locate=locate,
            mode=mode,
        )

        if resp := await cap(req):
            print_resp(resp, ctx)
        else:
            console.print(f"[yellow]No {mode.replace('_', ' ')} found[/yellow]")


@app.command(
    "hover",
    help="Get documentation and type information (hover) for a symbol at a specific location.",
)
@cli_syncify
async def get_hover(
    ctx: typer.Context,
    file_path: op.FileArg,
    scope: op.ScopeOpt = None,
    find: op.FindOpt = None,
    marker: op.MarkerOpt = "<HERE>",
):
    locate = create_locate(file_path, scope, find, marker)

    async with init_client(file_path) as client:
        if not isinstance(client, HoverClient):
            console.print("[red]Error:[/red] Client does not support hover")
            raise typer.Exit(1)

        cap = HoverCapability(client)
        req = HoverRequest(locate=locate)

        if resp := await cap(req):
            print_resp(resp, ctx)
        else:
            console.print("[yellow]No hover information found[/yellow]")


@app.command(
    "reference",
    help="Find references (default) or implementations (--impl) of a symbol. (alias: ref)",
)
@app.command("ref", hidden=True)
@cli_syncify
async def get_reference(
    ctx: typer.Context,
    file_path: op.FileArg,
    scope: op.ScopeOpt = None,
    find: op.FindOpt = None,
    marker: op.MarkerOpt = "<HERE>",
    mode: Annotated[
        Literal["references", "implementations"],
        typer.Option(
            "--mode",
            "-m",
            help="Search mode (default: references).",
            hidden=True,
        ),
    ] = "references",
    impl: bool = typer.Option(False, "--impl", help="Find concrete implementations."),
    references: bool = typer.Option(False, "--ref", help="Find all usages."),
    context_lines: Annotated[
        int | None,
        typer.Option(
            "--context-lines",
            "-C",
            help="Number of lines of context to show around each match.",
        ),
    ] = None,
    max_items: op.MaxItemsOpt = None,
    start_index: op.StartIndexOpt = 0,
    pagination_id: op.PaginationIdOpt = None,
):
    if impl and references:
        console.print("[red]Error:[/red] --impl and --ref are mutually exclusive")
        raise typer.Exit(1)

    if impl:
        mode = "implementations"
    elif references:
        mode = "references"

    locate = create_locate(file_path, scope, find, marker)

    async with init_client(file_path) as client:
        if not isinstance(client, ReferenceClient):
            console.print("[red]Error:[/red] Client does not support references")
            raise typer.Exit(1)

        cap = ReferenceCapability(client)

        effective_context_lines = (
            context_lines
            if context_lines is not None
            else settings.default_context_lines
        )

        req = ReferenceRequest(
            locate=locate,
            mode=mode,
            context_lines=effective_context_lines,
            max_items=max_items,
            start_index=start_index,
            pagination_id=pagination_id,
        )

        if resp := await cap(req):
            print_resp(resp, ctx)
        else:
            console.print(f"[yellow]No {mode} found[/yellow]")


@app.command(
    "outline",
    help="Get the hierarchical symbol outline (classes, functions, etc.) for a specific file.",
)
@cli_syncify
async def get_outline(
    ctx: typer.Context,
    file_path: op.FileArg,
    all_symbols: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Show all symbols including local variables and parameters.",
        ),
    ] = False,
):
    async with init_client(file_path) as client:
        if not isinstance(client, OutlineClient):
            console.print("[red]Error:[/red] Client does not support symbol outline")
            raise typer.Exit(1)

        cap = OutlineCapability(client)
        req = OutlineRequest(file_path=file_path)

        if resp := await cap(req):
            if resp.items:
                if not all_symbols:
                    filtered_items = [
                        item
                        for item in resp.items
                        if item.kind
                        in {
                            SymbolKind.Class,
                            SymbolKind.Function,
                            SymbolKind.Method,
                            SymbolKind.Interface,
                            SymbolKind.Enum,
                            SymbolKind.Module,
                            SymbolKind.Namespace,
                            SymbolKind.Struct,
                        }
                    ]
                    resp.items = filtered_items
                    if not filtered_items:
                        console.print(
                            "[yellow]No symbols found (use --all to show local variables)[/yellow]"
                        )
                        return
                print_resp(resp, ctx)
            else:
                console.print("[yellow]No symbols found[/yellow]")
        else:
            console.print("[yellow]No symbols found[/yellow]")


@app.command(
    "symbol",
    help="Get detailed symbol information at a specific location. (alias: sym)",
)
@app.command("sym", hidden=True)
@cli_syncify
async def get_symbol(
    ctx: typer.Context,
    file_path: op.FileArg,
    scope: op.ScopeOpt = None,
    find: op.FindOpt = None,
    marker: op.MarkerOpt = "<HERE>",
):
    locate = create_locate(file_path, scope, find, marker)

    async with init_client(file_path) as client:
        if not isinstance(client, SymbolClient):
            console.print("[red]Error:[/red] Client does not support symbol info")
            raise typer.Exit(1)

        cap = SymbolCapability(client)
        req = SymbolRequest(
            locate=locate,
        )

        if resp := await cap(req):
            print_resp(resp, ctx)
        else:
            console.print("[yellow]No symbol information found[/yellow]")


@app.command(
    "search",
    help="Search for symbols across the entire workspace by name query.",
)
@cli_syncify
async def search(
    ctx: typer.Context,
    query: Annotated[
        str,
        typer.Argument(help="The name or partial name of the symbol to search for."),
    ],
    workspace: op.WorkspaceOpt = None,
    kinds: Annotated[
        list[str] | None,
        typer.Option(
            "--kind",
            "-k",
            help="Filter by symbol kind (e.g., 'class', 'function'). Can be specified multiple times.",
        ),
    ] = None,
    max_items: op.MaxItemsOpt = None,
    start_index: op.StartIndexOpt = 0,
    pagination_id: op.PaginationIdOpt = None,
):
    if workspace is None:
        workspace = Path.cwd()

    async with init_client(workspace) as client:
        if not isinstance(client, SearchClient):
            console.print("[red]Error:[/red] Client does not support search")
            raise typer.Exit(1)

        cap = SearchCapability(client)

        effective_max_items = (
            max_items if max_items is not None else settings.default_max_items
        )

        req = SearchRequest(
            query=query,
            kinds=[SymbolKind(k) for k in kinds] if kinds else None,
            max_items=effective_max_items,
            start_index=start_index,
            pagination_id=pagination_id,
        )

        if resp := await cap(req):
            if resp.items:
                print_resp(resp, ctx)
                if effective_max_items and len(resp.items) >= effective_max_items:
                    console.print(
                        f"\n[dim]Showing {effective_max_items} results. Use --max-items to see more.[/dim]"
                    )
            else:
                console.print("[yellow]No matches found[/yellow]")
        else:
            console.print("[yellow]No matches found[/yellow]")


def run():
    try:
        app()
    except Exception as e:
        if settings.debug:
            raise

        def get_msg(err: Exception) -> str:
            if isinstance(err, ExceptionGroup):
                return "\n".join(get_msg(se) for se in err.exceptions)
            msg = str(err)
            if not msg:
                msg = f"{type(err).__name__}: An error occurred"
            return msg

        console.print(f"[red]Error:[/red] {get_msg(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run()
