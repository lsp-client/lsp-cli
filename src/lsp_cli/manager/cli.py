from __future__ import annotations

from typing import Final

from litestar import Litestar, delete, get, post
from litestar.datastructures import State
from litestar.di import Provide
from loguru import logger

from lsp_cli.settings import LOG_DIR, settings

from . import get_manager, manager_lifespan
from .models import (
    CreateClientRequest,
    CreateClientResponse,
    DeleteClientRequest,
    DeleteClientResponse,
    ManagedClientInfo,
)

logger.add(
    LOG_DIR / "manager.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
)


@post("/create", status_code=201)
async def create_client_handler(
    data: CreateClientRequest, state: State
) -> CreateClientResponse:
    manager = get_manager(state)
    uds_path = await manager.create_client(data.path)
    info = manager.inspect_client(data.path)
    if not info:
        raise RuntimeError("Failed to create client")

    return CreateClientResponse(uds_path=uds_path, info=info)


@delete("/delete", status_code=200)
async def delete_client_handler(
    data: DeleteClientRequest, state: State
) -> DeleteClientResponse:
    manager = get_manager(state)
    info = manager.inspect_client(data.path)
    await manager.delete_client(data.path)

    return DeleteClientResponse(info=info)


@get("/list")
async def list_clients_handler(state: State) -> list[ManagedClientInfo]:
    manager = get_manager(state)
    return manager.list_clients()


app: Final = Litestar(
    route_handlers=[
        create_client_handler,
        delete_client_handler,
        list_clients_handler,
    ],
    dependencies={"manager": Provide(get_manager, sync_to_thread=False)},
    lifespan=[manager_lifespan],
    debug=settings.debug,
)
