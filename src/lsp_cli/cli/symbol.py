from lsap.schema.symbol import SymbolRequest, SymbolResponse
from lsp_cli.utils.sync import cli_syncify
from .. import options as op
from .shared import managed_client, create_locate, print_resp


@cli_syncify
async def get_symbol(
    locate: op.LocateOpt,
):
    """
    Get detailed symbol information at a specific location. (alias: sym)
    """
    locate_obj = create_locate(locate)

    async with managed_client(locate_obj.file_path) as client:
        resp_obj = await client.post(
            "/symbol", SymbolResponse, json=SymbolRequest(locate=locate_obj)
        )

    if resp_obj:
        print_resp(resp_obj)
    else:
        print("Warning: No symbol information found")
