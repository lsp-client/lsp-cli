from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import asyncer
from attrs import Factory, define, field
from litestar.exceptions import NotFoundException
from loguru import logger

from lsp_cli.client import find_client
from lsp_cli.settings import LOG_DIR, settings

from .client import ManagedClient, get_client_id
from .models import ManagedClientInfo


@define
class Manager:
    _clients: dict[str, ManagedClient] = Factory(dict)
    _tg: asyncer.TaskGroup = field(init=False)
    _logger_sink_id: int = field(init=False)

    def __attrs_post_init__(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / "manager.log"
        log_level = settings.effective_log_level
        self._logger_sink_id = logger.add(
            log_path,
            rotation="10 MB",
            retention="1 day",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True,
        )
        logger.info(
            f"[Manager] Manager log initialized at {log_path} (level: {log_level})"
        )

    async def create_client(self, path: Path) -> Path:
        target = find_client(path)
        if not target:
            raise NotFoundException(f"No LSP client found for path: {path}")

        logger.debug(f"[Manager] Found client target: {target}")

        logger.debug(target.client_cls.mro())

        client_id = get_client_id(target)
        if client_id not in self._clients:
            logger.info(f"[Manager] Creating new client: {client_id}")
            m_client = ManagedClient(target)
            self._clients[client_id] = m_client
            self._tg.soonify(self._run_client)(m_client)
        else:
            logger.info(f"[Manager] Reusing existing client: {client_id}")
            self._clients[client_id]._reset_timeout()

        return self._clients[client_id].uds_path

    @logger.catch(level="ERROR")
    async def _run_client(self, client: ManagedClient) -> None:
        try:
            logger.info(f"[Manager] Running client: {client.id}")
            await client.run()
        except Exception as e:
            logger.exception(f"[Manager] Error running client {client.id}: {e}")
            raise
        finally:
            logger.info(f"[Manager] Removing client: {client.id}")
            self._clients.pop(client.id, None)

    async def delete_client(self, path: Path):
        if target := find_client(path):
            client_id = get_client_id(target)
            if client := self._clients.get(client_id):
                logger.info(f"[Manager] Stopping client: {client_id}")
                client.stop()

    def inspect_client(self, path: Path) -> ManagedClientInfo | None:
        if target := find_client(path):
            client_id = get_client_id(target)
            if client := self._clients.get(client_id):
                return client.info
        return None

    def list_clients(self) -> list[ManagedClientInfo]:
        return [client.info for client in self._clients.values()]

    @asynccontextmanager
    async def run(self):
        logger.info("[Manager] Starting manager")
        try:
            async with asyncer.create_task_group() as tg:
                self._tg = tg
                yield self
        finally:
            logger.info("[Manager] Shutting down manager")
            logger.remove(self._logger_sink_id)
