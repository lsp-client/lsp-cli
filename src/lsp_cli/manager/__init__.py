from __future__ import annotations

import subprocess
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import anyio
import httpx
from litestar import Litestar
from litestar.datastructures import State

from lsp_cli.settings import LOG_DIR, MANAGER_UDS_PATH
from lsp_cli.utils.socket import is_socket_alive

from .manager import Manager
from .models import (
    CreateClientRequest,
    CreateClientResponse,
    DeleteClientRequest,
    DeleteClientResponse,
    ManagedClientInfo,
)

__all__ = [
    "Manager",
    "ManagedClientInfo",
    "CreateClientRequest",
    "CreateClientResponse",
    "DeleteClientRequest",
    "DeleteClientResponse",
    "connect_manager",
    "get_manager",
    "manager_lifespan",
]


@asynccontextmanager
async def manager_lifespan(app: Litestar) -> AsyncGenerator[None]:
    await anyio.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    async with Manager().run() as manager:
        app.state.manager = manager
        yield


def get_manager(state: State) -> Manager:
    return cast(Manager, state.manager)


def connect_manager() -> httpx.Client:
    if not is_socket_alive(MANAGER_UDS_PATH):
        subprocess.Popen(
            (sys.executable, "-m", "lsp_cli.manager"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    return httpx.Client(
        transport=httpx.HTTPTransport(uds=str(MANAGER_UDS_PATH), retries=5),
        base_url="http://localhost",
    )
