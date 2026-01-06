from pathlib import Path
from typing import Annotated

import typer

FileArg = Annotated[
    Path,
    typer.Argument(
        help="Path to a code file or a project directory",
    ),
]

WorkspaceOpt = Annotated[
    Path | None,
    typer.Option(
        "--workspace",
        "-w",
        help="Path to the workspace or a file within it to identify the project. Defaults to current directory.",
    ),
]

ScopeOpt = Annotated[
    str | None,
    typer.Option(
        "--scope",
        "-s",
        help="Scope: 1-based line (e.g. '1'), line range (e.g. '1,10'), or symbol path (e.g. 'a.b.c')",
    ),
]

FindOpt = Annotated[
    str | None,
    typer.Option(
        "--find",
        "-f",
        help="Text snippet to find",
    ),
]

MarkerOpt = Annotated[
    str,
    typer.Option(
        "--marker",
        help="Position marker in find pattern",
    ),
]

MaxItemsOpt = Annotated[
    int | None,
    typer.Option(
        "--max-items",
        "-n",
        help="Max items to return",
    ),
]

StartIndexOpt = Annotated[
    int,
    typer.Option(
        "--start-index",
        "-i",
        help="Pagination offset",
    ),
]

PaginationIdOpt = Annotated[
    str | None,
    typer.Option(
        "--pagination-id",
        "-p",
        help="Pagination token",
    ),
]

MarkdownOpt = Annotated[
    bool,
    typer.Option(
        "--markdown",
        "-m",
        help="Render output as Markdown.",
    ),
]
