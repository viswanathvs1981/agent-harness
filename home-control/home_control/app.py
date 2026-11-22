from __future__ import annotations

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


def create_app(instance: Hub | None = None) -> FastAPI:
    app = FastAPI(title="Room", version="0.1.0")
    state = instance or hub

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
        result = await state.chat_async(body.message)
        return result.to_dict()

    return app


app = create_app(hub)
