from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from home_control.hub import Hub

WEB = Path(__file__).resolve().parent / "web"
hub = Hub(demo=False)


class ScanBody(BaseModel):
    deep: bool = False


class CommandBody(BaseModel):
    action: str
    value: Any = None


class ChatBody(BaseModel):
    message: str = Field(min_length=1)
    device_id: str | None = None


class LayoutBody(BaseModel):
    pins: list[str] | None = None
    device_order: list[str] | None = None


def create_app(instance: Hub | None = None, monitor: bool = False) -> FastAPI:
    state = instance or hub

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        task = None
        if monitor:
            task = asyncio.create_task(_poll(state))
        try:
            yield
        finally:
            if task is not None:
                task.cancel()

    app = FastAPI(title="Room", version="0.1.0", lifespan=lifespan)

    if WEB.exists():
        app.mount("/assets", StaticFiles(directory=WEB), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "demo": state.demo,
            "lan_ip": state.lan_ip(),
            "devices": len(state.devices),
            "hint": state.hint(),
            "error": state.last_error,
            "brain": "claude" if state.anthropic_key else "rules",
            "model": state.anthropic_model if state.anthropic_key else None,
        }

    @app.get("/api/devices")
    def list_devices() -> dict[str, Any]:
        return {"devices": [item.to_dict() for item in state.snapshot()]}

    @app.post("/api/scan")
    async def scan(body: ScanBody | None = None) -> dict[str, Any]:
        deep = body.deep if body else False
        devices = await state.scan(deep=deep)
        return {
            "devices": [item.to_dict() for item in devices],
            "deep": deep,
            "hint": state.hint(),
            "error": state.last_error,
        }

    @app.post("/api/devices/{device_id}/command")
    def command(device_id: str, body: CommandBody) -> dict[str, Any]:
        result = state.command(device_id, body.action, body.value)
        if result.device_id is None and not result.ok:
            raise HTTPException(status_code=404, detail=result.message)
        return result.to_dict()

    @app.post("/api/chat")
    async def chat(body: ChatBody) -> dict[str, Any]:
        result = await state.chat_async(body.message, selected_id=body.device_id)
        return result.to_dict()

    @app.get("/api/dashboard")
    async def dashboard() -> dict[str, Any]:
        await state.tick()
        return state.dashboard()

    @app.put("/api/layout")
    def layout(body: LayoutBody) -> dict[str, Any]:
        return state.set_layout(pins=body.pins, device_order=body.device_order)

    return app


async def _poll(state: Hub) -> None:
    while True:
        try:
            await state.tick()
        except Exception:
            pass
        await asyncio.sleep(8 if state.demo else 20)


app = create_app(hub)
