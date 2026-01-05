from __future__ import annotations

from pathlib import Path

from lsp_client.jsonrpc.types import RawNotification, RawRequest, RawResponsePackage
from pydantic import BaseModel
from rich import box
from rich.table import Table


class ManagedClientInfo(BaseModel):
    project_path: Path
    language: str
    remaining_time: float

    @classmethod
    def format(cls, data: list[ManagedClientInfo] | ManagedClientInfo) -> Table:
        table = Table(box=box.ROUNDED)
        table.add_column("Language", style="cyan")
        table.add_column("Project Path", style="green")
        table.add_column("Remaining Time", style="magenta", justify="right")

        infos = [data] if isinstance(data, ManagedClientInfo) else data

        for info in infos:
            table.add_row(
                info.language,
                str(info.project_path),
                f"{info.remaining_time:.1f}s",
            )
        return table


class CreateClientRequest(BaseModel):
    path: Path


class CreateClientResponse(BaseModel):
    uds_path: Path
    info: ManagedClientInfo


class DeleteClientRequest(BaseModel):
    path: Path


class DeleteClientResponse(BaseModel):
    info: ManagedClientInfo | None


class LspRequest(BaseModel):
    payload: RawRequest


class LspResponse(BaseModel):
    payload: RawResponsePackage


class LspNotification(BaseModel):
    payload: RawNotification
