from functools import partial

from litestar import Controller, post
from litestar.di import Provide
from lsap.capability.abc import Capability
from lsap.capability.definition import (
    DefinitionCapability,
    DefinitionRequest,
    DefinitionResponse,
)
from lsap.capability.hover import HoverCapability, HoverRequest, HoverResponse
from lsap.capability.locate import LocateCapability, LocateRequest, LocateResponse
from lsap.capability.outline import OutlineCapability, OutlineRequest, OutlineResponse
from lsap.capability.reference import (
    ReferenceCapability,
    ReferenceRequest,
    ReferenceResponse,
)
from lsap.capability.rename import (
    RenameExecuteCapability,
    RenameExecuteRequest,
    RenameExecuteResponse,
    RenamePreviewCapability,
    RenamePreviewRequest,
    RenamePreviewResponse,
)
from lsap.capability.search import SearchCapability, SearchRequest, SearchResponse
from lsap.capability.symbol import SymbolCapability, SymbolRequest, SymbolResponse
from lsp_client import Client


def init_capability(cap_cls: type[Capability], client: Client):
    return cap_cls(client)


class CapabilityController(Controller):
    path = "/capability"

    dependencies = {
        "definition": Provide(partial(DefinitionCapability)),
        "hover": Provide(partial(HoverCapability)),
        "locate": Provide(partial(LocateCapability)),
        "outline": Provide(partial(OutlineCapability)),
        "reference": Provide(partial(ReferenceCapability)),
        "rename_preview": Provide(partial(RenamePreviewCapability)),
        "rename_execute": Provide(partial(RenameExecuteCapability)),
        "search": Provide(partial(SearchCapability)),
        "symbol": Provide(partial(SymbolCapability)),
    }

    @post("/definition")
    async def definition(
        self, req: DefinitionRequest, definition: DefinitionCapability
    ) -> DefinitionResponse | None:
        return await definition(req)

    @post("/hover")
    async def hover(
        self, req: HoverRequest, hover: HoverCapability
    ) -> HoverResponse | None:
        return await hover(req)

    @post("/locate")
    async def locate(
        self, req: LocateRequest, locate: LocateCapability
    ) -> LocateResponse | None:
        return await locate(req)

    @post("/outline")
    async def outline(
        self, req: OutlineRequest, outline: OutlineCapability
    ) -> OutlineResponse | None:
        return await outline(req)

    @post("/reference")
    async def reference(
        self, req: ReferenceRequest, reference: ReferenceCapability
    ) -> ReferenceResponse | None:
        return await reference(req)

    @post("/rename/preview")
    async def rename_preview(
        self, req: RenamePreviewRequest, rename_preview: RenamePreviewCapability
    ) -> RenamePreviewResponse | None:
        return await rename_preview(req)

    @post("/rename/execute")
    async def rename_execute(
        self, req: RenameExecuteRequest, rename_execute: RenameExecuteCapability
    ) -> RenameExecuteResponse | None:
        return await rename_execute(req)

    @post("/search")
    async def search(
        self, req: SearchRequest, search: SearchCapability
    ) -> SearchResponse | None:
        return await search(req)

    @post("/symbol")
    async def symbol(
        self, req: SymbolRequest, symbol: SymbolCapability
    ) -> SymbolResponse | None:
        return await symbol(req)
