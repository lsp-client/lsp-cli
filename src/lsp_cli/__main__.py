import sys

import typer

from lsp_cli.cli import (
    definition,
    hover,
    locate,
    outline,
    reference,
    rename,
    search,
    symbol,
)
from lsp_cli.cli.main import main_callback
from lsp_cli.cli.shared import get_msg
from lsp_cli.server import app as server_app
from lsp_cli.settings import settings

app = typer.Typer(
    help="LSP CLI: A command-line tool for interacting with Language Server Protocol (LSP) features.",
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 1000,
        "terminal_width": 1000,
    },
    add_completion=False,
    pretty_exceptions_enable=False,
)

# Set callback
app.callback(invoke_without_command=True)(main_callback)

# Add sub-typers
app.add_typer(server_app, name="server")
app.add_typer(rename.app, name="rename")

# Register commands
app.command("locate")(locate.locate_command)
app.command("definition")(definition.get_definition)
app.command("def", hidden=True)(definition.get_definition)
app.command("hover")(hover.get_hover)
app.command("reference")(reference.get_reference)
app.command("ref", hidden=True)(reference.get_reference)
app.command("outline")(outline.get_outline)
app.command("symbol")(symbol.get_symbol)
app.command("sym", hidden=True)(symbol.get_symbol)
app.command("search")(search.search)


def run():
    try:
        app()
    except (typer.Exit, typer.Abort):
        pass
    except Exception as e:
        if settings.debug:
            raise e
        print(f"Error: {get_msg(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
