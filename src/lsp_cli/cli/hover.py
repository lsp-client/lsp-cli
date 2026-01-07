from lsap.schema.hover import HoverRequest, HoverResponse
from lsp_cli.utils.sync import cli_syncify
from .. import options as op
from .shared import managed_client, create_locate, print_resp


@cli_syncify
async def get_hover(
    locate: op.LocateOpt,
):
    """
    Get documentation and type information (hover) for a symbol at a specific location.
    """
    locate_obj = create_locate(locate)

    async with managed_client(locate_obj.file_path) as client:
        resp_obj = await client.post(
            "/hover", HoverResponse, json=HoverRequest(locate=locate_obj)
        )

    if resp_obj:
        print_resp(resp_obj)
    else:
        print("Warning: No hover information found")
