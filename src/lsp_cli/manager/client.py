from __future__ import annotations

from pathlib import Path

import anyio
import asyncer
import loguru
import lsp_client
import uvicorn
import xxhash
from attrs import define, field
from litestar import Litestar, get, post
from litestar.datastructures import State
from loguru import logger as global_logger
from lsap.capability.definition import DefinitionCapability, DefinitionClient
from lsap.capability.hover import HoverCapability, HoverClient
from lsap.capability.locate import LocateCapability, LocateClient
from lsap.capability.outline import OutlineCapability, OutlineClient
from lsap.capability.reference import ReferenceCapability, ReferenceClient
from lsap.capability.rename import (
    RenameExecuteCapability,
    RenamePreviewCapability,
    RenameClient,
)
from lsap.capability.search import SearchCapability, SearchClient
from lsap.capability.symbol import SymbolCapability, SymbolClient
from lsap.schema.definition import DefinitionRequest, DefinitionResponse
from lsap.schema.hover import HoverRequest, HoverResponse
from lsap.schema.locate import LocateRequest, LocateResponse
from lsap.schema.outline import OutlineRequest, OutlineResponse
from lsap.schema.reference import ReferenceRequest, ReferenceResponse
from lsap.schema.rename import (
    RenameExecuteRequest,
    RenameExecuteResponse,
    RenamePreviewRequest,
    RenamePreviewResponse,
)
from lsap.schema.search import SearchRequest, SearchResponse
from lsap.schema.symbol import SymbolRequest, SymbolResponse
from lsp_client import Client

from lsp_cli.client import TargetClient
from lsp_cli.settings import LOG_DIR, RUNTIME_DIR, settings

from .models import ManagedClientInfo


def get_client_id(target: TargetClient) -> str:
    kind = target.client_cls.get_language_config().kind
    path_hash = xxhash.xxh32_hexdigest(target.project_path.as_posix())
    return f"{kind.value}-{path_hash}-default"


@define
class ManagedClient:
    target: TargetClient

    _server: uvicorn.Server = field(init=False)
    _timeout_scope: anyio.CancelScope = field(init=False)
    _server_scope: anyio.CancelScope = field(init=False)

    _deadline: float = field(init=False)
    _should_exit: bool = False

    _logger: loguru.Logger = field(init=False)
    _logger_sink_id: int = field(init=False)

    def __attrs_post_init__(self) -> None:
        self._deadline = anyio.current_time() + settings.idle_timeout

        client_log_dir = LOG_DIR / "clients"
        client_log_dir.mkdir(parents=True, exist_ok=True)

        log_path = client_log_dir / f"{self.id}.log"
        log_level = settings.effective_log_level
        self._logger_sink_id = global_logger.add(
            log_path,
            rotation="10 MB",
            retention="1 day",
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>",
            enqueue=True,
        )
        self._logger = global_logger.bind(client_id=self.id)
        self._logger.info("Client log initialized at {}", log_path)

    @property
    def id(self) -> str:
        return get_client_id(self.target)

    @property
    def uds_path(self) -> Path:
        return RUNTIME_DIR / f"{self.id}.sock"

    @property
    def info(self) -> ManagedClientInfo:
        return ManagedClientInfo(
            project_path=self.target.project_path,
            language=self.target.client_cls.get_language_config().kind.value,
            remaining_time=max(0.0, self._deadline - anyio.current_time()),
        )

    def stop(self) -> None:
        self._logger.info("Stopping managed client")
        self._should_exit = True
        self._server.should_exit = True
        self._server_scope.cancel()
        self._timeout_scope.cancel()

    def _reset_timeout(self) -> None:
        self._deadline = anyio.current_time() + settings.idle_timeout
        self._timeout_scope.cancel()

    async def _timeout_loop(self) -> None:
        while not self._should_exit:
            if self._server.should_exit:
                break
            remaining = self._deadline - anyio.current_time()
            if remaining <= 0:
                break
            with anyio.CancelScope() as scope:
                self._timeout_scope = scope
                await anyio.sleep(remaining)

        self._server.should_exit = True
        self._server_scope.cancel()

    def _create_app(self, client: Client) -> Litestar:
        @get("/health")
        async def health() -> str:
            return "ok"

        @post("/shutdown")
        async def shutdown() -> None:
            self._logger.info("Shutdown requested")
            self.stop()

        @post("/locate")
        async def handle_locate(
            state: State, data: LocateRequest
        ) -> LocateResponse | None:
            self._reset_timeout()
            if not isinstance(client, LocateClient):
                raise TypeError("Client does not support locate capability")
            if not state.locate:
                state.locate = LocateCapability(client)
            assert isinstance(state.locate, LocateCapability)

            return await state.locate(data)

        @post("/definition")
        async def handle_definition(
            state: State,
            data: DefinitionRequest,
        ) -> DefinitionResponse | None:
            self._reset_timeout()
            if not isinstance(client, DefinitionClient):
                raise TypeError("Client does not support definition capability")
            if not state.definition:
                state.definition = DefinitionCapability(client)
            assert isinstance(state.definition, DefinitionCapability)

            return await state.definition(data)

        @post("/hover")
        async def handle_hover(
            state: State, data: HoverRequest
        ) -> HoverResponse | None:
            self._reset_timeout()
            if not isinstance(client, HoverClient):
                raise TypeError("Client does not support hover capability")
            if not state.hover:
                state.hover = HoverCapability(client)
            assert isinstance(state.hover, HoverCapability)

            return await state.hover(data)

        @post("/reference")
        async def handle_reference(
            state: State, data: ReferenceRequest
        ) -> ReferenceResponse | None:
            self._reset_timeout()
            if not isinstance(client, ReferenceClient):
                raise TypeError("Client does not support reference capability")
            if not state.reference:
                state.reference = ReferenceCapability(client)
            assert isinstance(state.reference, ReferenceCapability)

            return await state.reference(data)

        @post("/outline")
        async def handle_outline(
            state: State, data: OutlineRequest
        ) -> OutlineResponse | None:
            self._reset_timeout()
            if not isinstance(client, OutlineClient):
                raise TypeError("Client does not support outline capability")
            if not state.outline:
                state.outline = OutlineCapability(client)
            assert isinstance(state.outline, OutlineCapability)

            return await state.outline(data)

        @post("/symbol")
        async def handle_symbol(
            state: State, data: SymbolRequest
        ) -> SymbolResponse | None:
            self._reset_timeout()
            if not isinstance(client, SymbolClient):
                raise TypeError("Client does not support symbol capability")
            if not state.symbol:
                state.symbol = SymbolCapability(client)
            assert isinstance(state.symbol, SymbolCapability)

            return await state.symbol(data)

        @post("/search")
        async def handle_search(
            state: State, data: SearchRequest
        ) -> SearchResponse | None:
            self._reset_timeout()
            if not isinstance(client, SearchClient):
                raise TypeError("Client does not support search capability")
            if not state.search:
                state.search = SearchCapability(client)
            assert isinstance(state.search, SearchCapability)

            return await state.search(data)

        @post("/rename/preview")
        async def handle_rename_preview(
            state: State,
            data: RenamePreviewRequest,
        ) -> RenamePreviewResponse | None:
            self._reset_timeout()
            if not isinstance(client, RenameClient):
                raise TypeError("Client does not support rename capability")
            if not state.rename_preview:
                state.rename_preview = RenamePreviewCapability(client)
            assert isinstance(state.rename_preview, RenamePreviewCapability)

            return await state.rename_preview(data)

        @post("/rename/execute")
        async def handle_rename_execute(
            state: State,
            data: RenameExecuteRequest,
        ) -> RenameExecuteResponse | None:
            self._reset_timeout()
            if not isinstance(client, RenameClient):
                raise TypeError("Client does not support rename capability")
            if not state.rename_execute:
                state.rename_execute = RenameExecuteCapability(client)
            assert isinstance(state.rename_execute, RenameExecuteCapability)

            return await state.rename_execute(data)

        return Litestar(
            route_handlers=[
                health,
                shutdown,
                handle_locate,
                handle_definition,
                handle_hover,
                handle_reference,
                handle_outline,
                handle_symbol,
                handle_search,
                handle_rename_preview,
                handle_rename_execute,
            ],
            debug=settings.debug,
        )

    async def _serve(self, client: Client) -> None:
        app = self._create_app(client)

        config = uvicorn.Config(
            app,
            uds=str(self.uds_path),
            loop="asyncio",
        )
        self._server = uvicorn.Server(config)

        async with asyncer.create_task_group() as tg:
            with anyio.CancelScope() as scope:
                self._server_scope = scope
                tg.soonify(self._timeout_loop)()
                await self._server.serve()

    async def run(self) -> None:
        self._logger.info(
            "Starting managed client for project {} at {}",
            self.target.project_path,
            self.uds_path,
        )

        uds_path = anyio.Path(self.uds_path)
        await uds_path.unlink(missing_ok=True)
        await uds_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            lsp_client.enable_logging()
            self._logger.debug("Client MRO: {}", self.target.client_cls.mro())
            async with self.target.client_cls(
                workspace=self.target.project_path
            ) as client:
                self._logger.info("LSP client initialized successfully")
                await self._serve(client)
        finally:
            self._logger.info("Cleaning up client")
            await uds_path.unlink(missing_ok=True)
            self._logger.remove(self._logger_sink_id)
            self._timeout_scope.cancel()
            self._server_scope.cancel()
