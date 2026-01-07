from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from lsap.schema.locate import Locate
from lsap.utils.locate import parse_locate_string
from pydantic import ValidationError

from lsp_cli.manager import CreateClientRequest, CreateClientResponse
from lsp_cli.server import get_manager_client
from lsp_cli.utils.http import AsyncHttpClient


@asynccontextmanager
async def managed_client(path: Path) -> AsyncGenerator[AsyncHttpClient]:
    path = path.absolute()
    with get_manager_client() as client:
        info = client.post(
            "/create",
            CreateClientResponse,
            json=CreateClientRequest(path=path),
        )
        assert info is not None

    transport = httpx.AsyncHTTPTransport(uds=info.uds_path.as_posix())
    async with AsyncHttpClient(
        httpx.AsyncClient(transport=transport, base_url="http://localhost")
    ) as client:
        yield client


def create_locate(locate_str: str) -> Locate:
    return parse_locate_string(locate_str)


def print_resp(resp):
    print(resp.format())


def get_msg(err: Exception | ExceptionGroup) -> str:
    match err:
        case ExceptionGroup():
            return "\n".join(get_msg(se) for se in err.exceptions)
        case ValidationError():
            return "\n".join(str(e["msg"]) for e in err.errors())
        case httpx.HTTPStatusError():
            try:
                data = err.response.json()
                if isinstance(data, dict) and "detail" in data:
                    return str(data["detail"])
            except Exception:
                pass
            return str(err)
        case _:
            return str(err)
