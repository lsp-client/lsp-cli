import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

import typer
from loguru import logger
from lsap.definition import DefinitionCapability, DefinitionClient
from lsap.hover import HoverCapability, HoverClient
from lsap.locate import LocateCapability
from lsap.outline import OutlineCapability, OutlineClient
from lsap.reference import ReferenceCapability, ReferenceClient
from lsap.rename import RenameCapability, RenameClient
from lsap.search import SearchCapability, SearchClient
from lsap.symbol import SymbolCapability, SymbolClient
from lsap.utils.locate import parse_locate_string
from lsap_schema.definition import DefinitionRequest
from lsap_schema.hover import HoverRequest
from lsap_schema.locate import Locate, LocateRequest
from lsap_schema.models import SymbolKind
from lsap_schema.outline import OutlineRequest
from lsap_schema.reference import ReferenceRequest
from lsap_schema.rename import (
    RenameExecuteRequest,
    RenamePreviewRequest,
    RenamePreviewResponse,
    RenameRequest,
)
from lsap_schema.search import SearchRequest
from lsap_schema.symbol import SymbolRequest
from lsp_client import Client

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
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 1000,
        "terminal_width": 1000,
    },
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
app.add_typer(server_app, name="server")


@asynccontextmanager
async def init_client(path: Path) -> AsyncGenerator[Client]:
    path = path.absolute()
    if not (target := find_client(path)):
        raise RuntimeError(f"No LSP client for {path}")

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


def create_locate(locate_str: str) -> Locate:
    return parse_locate_string(locate_str)


def print_code_context(file_path: Path, line: int, context: int = 3):
    if not file_path.exists():
        return
    try:
        lines = file_path.read_text().splitlines()
        start = max(0, line - 1 - context)
        end = min(len(lines), line + context)
        for i in range(start, end):
            prefix = "> " if i == line - 1 else "  "
            print(f"{prefix}{i + 1:4} | {lines[i]}")
    except Exception as e:
        logger.warning(f"Could not print code context: {e}")


def print_resp(resp):
    print(resp.format())


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable verbose debug logging for troubleshooting.",
    ),
):
    if debug:
        settings.debug = True

    logger.remove()
    logger.add(sys.stderr, level=settings.effective_log_level)

    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()


@app.command(
    "locate",
    help="""
Locate a position or range in the codebase using a string syntax.

Syntax: `<file_path>[:<scope>][@<find>]`

Scope formats:

- `<line>` - Single line number (e.g., `42`)

- `<start>,<end>` - Line range with comma (e.g., `10,20`)

- `<start>-<end>` - Line range with dash (e.g., `10-20`)

- `<symbol_path>` - Symbol path with dots (e.g., `MyClass.my_method`)

Examples:

- `foo.py@self.<|>`

- `foo.py:42@return <|>result`

- `foo.py:10,20@if <|>condition`

- `foo.py:MyClass.my_method@self.<|>`

- `foo.py:MyClass`
""",
)
@cli_syncify
async def locate_command(
    locate: Annotated[str, typer.Argument(help="The locate string to parse.")],
    check: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Verify if the target exists in the file and show its context.",
    ),
):
    locate_obj = create_locate(locate)
    resp = None
    error_msg = None

    try:
        async with init_client(locate_obj.file_path) as client:
            cap = LocateCapability(client)  # type: ignore
            req = LocateRequest(locate=locate_obj)
            resp = await cap(req)
            if not resp and check:
                error_msg = f"Target '{locate}' not found"
    except Exception as e:
        if check:
            error_msg = get_msg(e)

    if resp:
        print_resp(resp)
        print_code_context(resp.file_path, resp.position.line)
    elif error_msg:
        raise RuntimeError(error_msg)
    else:
        print(locate_obj)


@app.command(
    "definition",
    help="Find the definition (default), declaration (--decl), or type definition (--type) of a symbol. (alias: def)",
)
@app.command("def", hidden=True)
@cli_syncify
async def get_definition(
    locate: op.LocateOpt,
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
        raise ValueError("--decl and --type are mutually exclusive")

    if decl:
        mode = "declaration"
    elif type_def:
        mode = "type_definition"

    locate_obj = create_locate(locate)

    async with init_client(locate_obj.file_path) as client:
        if not isinstance(client, DefinitionClient):
            raise RuntimeError("Client does not support definitions")

        cap = DefinitionCapability(client)
        req = DefinitionRequest(
            locate=locate_obj,
            mode=mode,
        )

        if resp := await cap(req):
            print_resp(resp)
        else:
            print(f"Warning: No {mode.replace('_', ' ')} found")


@app.command(
    "hover",
    help="Get documentation and type information (hover) for a symbol at a specific location.",
)
@cli_syncify
async def get_hover(
    locate: op.LocateOpt,
):
    locate_obj = create_locate(locate)

    async with init_client(locate_obj.file_path) as client:
        if not isinstance(client, HoverClient):
            raise RuntimeError("Client does not support hover")

        cap = HoverCapability(client)
        req = HoverRequest(locate=locate_obj)

        if resp := await cap(req):
            print_resp(resp)
        else:
            print("Warning: No hover information found")


@app.command(
    "reference",
    help="Find references (default) or implementations (--impl) of a symbol. (alias: ref)",
)
@app.command("ref", hidden=True)
@cli_syncify
async def get_reference(
    locate: op.LocateOpt,
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
        raise ValueError("--impl and --ref are mutually exclusive")

    if impl:
        mode = "implementations"
    elif references:
        mode = "references"

    locate_obj = create_locate(locate)

    async with init_client(locate_obj.file_path) as client:
        if not isinstance(client, ReferenceClient):
            raise RuntimeError("Client does not support references")

        cap = ReferenceCapability(client)

        effective_context_lines = (
            context_lines
            if context_lines is not None
            else settings.default_context_lines
        )

        req = ReferenceRequest(
            locate=locate_obj,
            mode=mode,
            context_lines=effective_context_lines,
            max_items=max_items,
            start_index=start_index,
            pagination_id=pagination_id,
        )

        if resp := await cap(req):
            print_resp(resp)
        else:
            print(f"Warning: No {mode} found")


@app.command(
    "outline",
    help="Get the hierarchical symbol outline (classes, functions, etc.) for a specific file.",
)
@cli_syncify
async def get_outline(
    file_path: Annotated[
        Path,
        typer.Argument(help="Path to the file to get the symbol outline for."),
    ],
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
            raise RuntimeError("Client does not support symbol outline")

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
                        print(
                            "Warning: No symbols found (use --all to show local variables)"
                        )
                        return
                print_resp(resp)
            else:
                print("Warning: No symbols found")
        else:
            print("Warning: No symbols found")


@app.command(
    "symbol",
    help="Get detailed symbol information at a specific location. (alias: sym)",
)
@app.command("sym", hidden=True)
@cli_syncify
async def get_symbol(
    locate: op.LocateOpt,
):
    locate_obj = create_locate(locate)

    async with init_client(locate_obj.file_path) as client:
        if not isinstance(client, SymbolClient):
            raise RuntimeError("Client does not support symbol info")

        cap = SymbolCapability(client)
        req = SymbolRequest(
            locate=locate_obj,
        )

        if resp := await cap(req):
            print_resp(resp)
        else:
            print("Warning: No symbol information found")


@app.command(
    "search",
    help="Search for symbols across the entire workspace by name query.",
)
@cli_syncify
async def search(
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
            raise RuntimeError("Client does not support search")

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
                print_resp(resp)
                if effective_max_items and len(resp.items) >= effective_max_items:
                    print(
                        f"\nInfo: Showing {effective_max_items} results. Use --max-items to see more."
                    )
            else:
                print("Warning: No matches found")
        else:
            print("Warning: No matches found")


@app.command(
    "rename",
    help="Rename a symbol at a specific location.",
)
@cli_syncify
async def rename(
    new_name: Annotated[str, typer.Argument(help="The new name for the symbol.")],
    locate: op.LocateOpt,
    execute: Annotated[
        bool,
        typer.Option(
            "--execute",
            "-e",
            help="Execute the rename operation.",
        ),
    ] = False,
    rename_id: Annotated[
        str | None,
        typer.Option(
            "--id",
            help="Rename ID from a previous preview. If not provided and --execute is set, it will perform a preview first in the same session.",
        ),
    ] = None,
):
    locate_obj = create_locate(locate)

    async with init_client(locate_obj.file_path) as client:
        if not isinstance(client, RenameClient):
            raise RuntimeError("Client does not support rename")

        cap = RenameCapability(client)

        rid = rename_id
        if not rid:
            # Always do a preview first if no ID is provided to get the rename_id and see what will change
            preview_req = RenamePreviewRequest(locate=locate_obj, new_name=new_name)
            if resp := await cap(RenameRequest(root=preview_req)):
                preview_resp = resp.root
                if not isinstance(preview_resp, RenamePreviewResponse):
                    raise RuntimeError("Unexpected response from rename preview")

                rid = preview_resp.rename_id
                if not execute:
                    print_resp(preview_resp)
                    return
            else:
                print("Warning: No rename possibilities found at the location")
                return

        # If execute is requested (either via flag or ID), apply it
        execute_req = RenameExecuteRequest(
            locate=locate_obj,
            new_name=new_name,
            rename_id=rid,
        )
        if exec_resp := await cap(RenameRequest(root=execute_req)):
            print_resp(exec_resp.root)
        else:
            raise RuntimeError("Failed to execute rename")


def get_msg(err: Exception | ExceptionGroup) -> str:
    match err:
        case ExceptionGroup():
            return "\n".join(get_msg(se) for se in err.exceptions)
        case _:
            return str(err)


def run():
    try:
        app()
    except Exception as e:
        if settings.debug:
            raise e
        print(f"Error: {get_msg(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run()
