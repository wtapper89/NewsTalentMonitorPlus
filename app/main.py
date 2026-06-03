from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import ROOT_DIR, load_config
from app.logs import configure_logging, recent_logs
from app.services.dashboard import DashboardService
from app.services.ndi import NDIBridge
from app.services.photos import AnchorPhotoResolver
from app.services.room_sign import RoomSignService
from app.services.shure import MicboardAdapter, MockShureAdapter, QlxdAdapter, SystemApiAdapter
from app.store import DEFAULT_FIELDS, MappingStore, StateStore


def build_adapter(config, mapping_store: MappingStore):
    if config.source == "micboard":
        return MicboardAdapter(mapping_store)
    if config.source == "qlxd":
        return QlxdAdapter(mapping_store)
    if config.source == "system_api":
        return SystemApiAdapter(mapping_store)
    return MockShureAdapter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    configure_logging(config.log_level, config.log_file)
    mapping_store = MappingStore(config.mapping_file)
    service = DashboardService(
        adapter=build_adapter(config, mapping_store),
        store=StateStore(config.data_file),
        source=config.source,
        refresh_interval_seconds=config.refresh_interval_seconds,
        mapping_store=mapping_store,
    )
    ndi_bridge = NDIBridge()
    photo_resolver = AnchorPhotoResolver()
    room_sign_service = RoomSignService(mapping_store)

    stop_event = asyncio.Event()

    async def poll_forever() -> None:
        while not stop_event.is_set():
            state = await service.refresh()
            ndi_bridge.configure(state.get("display", {}))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=config.refresh_interval_seconds)
            except asyncio.TimeoutError:
                continue

    poll_task = asyncio.create_task(poll_forever())
    app.state.service = service
    app.state.mapping_store = mapping_store
    app.state.runtime_config = config
    app.state.ndi_bridge = ndi_bridge
    app.state.photo_resolver = photo_resolver
    app.state.room_sign_service = room_sign_service

    try:
        yield
    finally:
        stop_event.set()
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass
        ndi_bridge.stop()
        await room_sign_service.close()
        await service.close()


app = FastAPI(title="News Talent Monitor+", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT_DIR / "app" / "static"), name="static")


class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class AssignmentRequest(BaseModel):
    assigned_to: str = Field(default="", max_length=64)


class AuthConfigRequest(BaseModel):
    type: str = Field(default="bearer")
    token_url: str = Field(default="")
    grant_type: str = Field(default="client_credentials")
    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    scope: str = Field(default="")
    username: str = Field(default="")
    password: str = Field(default="")


class DefaultConnectionRequest(BaseModel):
    scheme: str = Field(default="tcp")
    port: int = Field(default=2202, ge=1, le=65535)


class MicboardConfigRequest(BaseModel):
    data_url: str = Field(default="http://127.0.0.1:8058/data.json")


class DisplayConfigRequest(BaseModel):
    show_title_mode: str = Field(default="manual", max_length=32)
    manual_show_title: str = Field(default="TVC NEWS", max_length=128)
    preview_mode: str = Field(default="placeholder", max_length=32)
    preview_url: str = Field(default="", max_length=1024)
    preview_source_name: str = Field(default="", max_length=255)
    preview_poster_url: str = Field(default="", max_length=1024)
    font_family: str = Field(default="Gotham, Montserrat, Arial, sans-serif", max_length=255)
    now_panel_enabled: bool = Field(default=True)
    now_panel_label: str = Field(default="Now", max_length=32)
    now_panel_border_color: str = Field(default="#1cff00", max_length=16)
    next_panel_enabled: bool = Field(default=True)
    next_panel_label: str = Field(default="Next", max_length=32)
    next_panel_border_color: str = Field(default="#fff200", max_length=16)
    status_sign_enabled: bool = Field(default=True)
    status_sign_custom_text: str = Field(default="", max_length=64)


class CompanionConfigRequest(BaseModel):
    enabled: bool = Field(default=False)
    base_url: str = Field(default="http://127.0.0.1:8000", max_length=255)
    connection_label: str = Field(default="Cuez", max_length=128)
    variable_name: str = Field(default="", max_length=128)
    on_air_source_variable_name: str = Field(default="", max_length=128)
    next_source_variable_name: str = Field(default="", max_length=128)
    status_sign_variable_name: str = Field(default="", max_length=128)


class AnchorPhotosConfigRequest(BaseModel):
    enabled: bool = Field(default=False)
    base_url: str = Field(default="", max_length=1024)
    share_path: str = Field(default="", max_length=1024)
    username: str = Field(default="", max_length=255)
    password: str = Field(default="", max_length=255)
    domain: str = Field(default="", max_length=255)
    timeout_seconds: int = Field(default=4, ge=1, le=30)


class RoomSignConfigRequest(BaseModel):
    enabled: bool = Field(default=False)
    room_name: str = Field(default="Studio", max_length=128)
    room_id: str = Field(default="", max_length=64)
    feed_url: str = Field(default="", max_length=2048)
    calendar_web_name: str = Field(default="", max_length=255)
    timezone: str = Field(default="America/New_York", max_length=128)
    lookahead_days: int = Field(default=7, ge=1, le=31)
    max_events: int = Field(default=6, ge=1, le=20)
    refresh_seconds: int = Field(default=60, ge=15, le=3600)


class MicConnectionRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    default_name: str = Field(min_length=1, max_length=64)
    receiver_name: str = Field(default="", max_length=64)
    channel_label: str = Field(default="", max_length=32)
    micboard_slot: int = Field(default=0, ge=0, le=64)
    receiver_channel: int = Field(default=1, ge=1, le=4)
    device_ip: str = Field(default="", max_length=255)
    scheme: str = Field(default="tcp")
    port: int = Field(default=2202, ge=1, le=65535)
    telemetry_path: str = Field(default="", max_length=255)
    telemetry_method: str = Field(default="GET", max_length=16)
    rename_path: str = Field(default="", max_length=255)
    rename_method: str = Field(default="PUT", max_length=16)
    assignment_variable_name: str = Field(default="", max_length=128)
    fields: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_FIELDS))
    rename_body: dict = Field(default_factory=lambda: {"name": "{name}"})


class ConfigUpdateRequest(BaseModel):
    micboard: MicboardConfigRequest = Field(default_factory=MicboardConfigRequest)
    display: DisplayConfigRequest = Field(default_factory=DisplayConfigRequest)
    companion: CompanionConfigRequest = Field(default_factory=CompanionConfigRequest)
    anchor_photos: AnchorPhotosConfigRequest = Field(default_factory=AnchorPhotosConfigRequest)
    room_sign: RoomSignConfigRequest = Field(default_factory=RoomSignConfigRequest)
    auth: AuthConfigRequest = Field(default_factory=AuthConfigRequest)
    default_connection: DefaultConnectionRequest = Field(default_factory=DefaultConnectionRequest)
    mics: list[MicConnectionRequest] = Field(default_factory=list)


def service_from(request: Request) -> DashboardService:
    return request.app.state.service


def mapping_store_from(request: Request) -> MappingStore:
    return request.app.state.mapping_store


def runtime_config_from(request: Request):
    return request.app.state.runtime_config


def adapter_from(request: Request):
    return request.app.state.service.adapter


def ndi_bridge_from(request: Request) -> NDIBridge:
    return request.app.state.ndi_bridge


def photo_resolver_from(request: Request) -> AnchorPhotoResolver:
    return request.app.state.photo_resolver


def room_sign_service_from(request: Request) -> RoomSignService:
    return request.app.state.room_sign_service


def build_config_response(request: Request) -> dict:
    mapping = mapping_store_from(request).load()
    runtime_config = runtime_config_from(request)
    service = service_from(request)
    mics = []
    for mic in mapping.get("mics", []):
        mic_payload = dict(mic)
        mic_payload["assigned_to"] = service.store.get_assignment(str(mic.get("id") or ""))
        mics.append(mic_payload)
    return {
        "source": runtime_config.source,
        "mapping_file": str(runtime_config.mapping_file),
        "micboard": mapping.get("micboard", {}),
        "display": mapping.get("display", {}),
        "companion": mapping.get("companion", {}),
        "anchor_photos": mapping.get("anchor_photos", {}),
        "room_sign": mapping.get("room_sign", {}),
        "default_connection": mapping.get("default_connection", {}),
        "auth": mapping.get("auth", {}),
        "mics": mics,
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(Path(ROOT_DIR / "app" / "static" / "index.html"))


@app.get("/dashboard")
async def dashboard_page() -> FileResponse:
    return FileResponse(Path(ROOT_DIR / "app" / "static" / "index.html"))


@app.get("/display")
async def display_page() -> FileResponse:
    return FileResponse(Path(ROOT_DIR / "app" / "static" / "display.html"))


@app.get("/config")
async def config_page() -> FileResponse:
    return FileResponse(Path(ROOT_DIR / "app" / "static" / "config.html"))


@app.get("/room-sign")
async def room_sign_page() -> FileResponse:
    return FileResponse(Path(ROOT_DIR / "app" / "static" / "room-sign.html"))


@app.get("/health")
async def health(request: Request) -> dict:
    state = await service_from(request).get_state()
    return {"status": state["connection_status"], "source": state["source"]}


@app.get("/api/state")
async def get_state(request: Request) -> dict:
    return await service_from(request).get_state()


@app.get("/api/config")
async def get_config(request: Request) -> dict:
    return build_config_response(request)


@app.post("/api/config")
async def save_config(payload: ConfigUpdateRequest, request: Request) -> dict:
    mapping_store_from(request).save(payload.model_dump())
    state = await service_from(request).refresh()
    ndi_bridge = ndi_bridge_from(request)
    if state.get("display", {}).get("preview_mode") != "ndi":
        ndi_bridge.stop()
    return {
        "config": build_config_response(request),
        "state": state,
        "ndi_status": ndi_bridge.status(),
    }


@app.post("/api/mics/{mic_id}/rename")
async def rename_mic(mic_id: str, payload: RenameRequest, request: Request) -> dict:
    try:
        return await service_from(request).rename_mic(mic_id, payload.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/mics/{mic_id}/assignment")
async def update_assignment(mic_id: str, payload: AssignmentRequest, request: Request) -> dict:
    try:
        return await service_from(request).update_assignment(mic_id, payload.assigned_to)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/companion/state")
async def get_companion_state(request: Request) -> dict:
    return await service_from(request).companion_state()


@app.get("/api/room-sign/state")
async def get_room_sign_state(request: Request) -> dict:
    state = await service_from(request).get_state()
    return await room_sign_service_from(request).state(state.get("display", {}))


@app.get("/api/ndi/status")
async def get_ndi_status(request: Request) -> dict:
    return ndi_bridge_from(request).status()


@app.get("/api/ndi/sources")
async def get_ndi_sources(request: Request) -> dict:
    bridge = ndi_bridge_from(request)
    try:
        sources = await asyncio.to_thread(bridge.discover_sources)
        return {"sources": sources}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/ndi/preview.mjpg")
async def get_ndi_preview(request: Request) -> StreamingResponse:
    bridge = ndi_bridge_from(request)

    async def stream():
        last_frame_at = 0.0
        while True:
            if await request.is_disconnected():
                break
            frame = bridge.latest_frame()
            if frame and frame.captured_at != last_frame_at:
                last_frame_at = frame.captured_at
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(frame.jpeg)}\r\n\r\n".encode("ascii")
                    + frame.jpeg
                    + b"\r\n"
                )
            await asyncio.sleep(0.01)

    return StreamingResponse(
        stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/ndi/latest.jpg")
async def get_ndi_latest(request: Request) -> Response:
    frame = ndi_bridge_from(request).latest_frame()
    if not frame:
        raise HTTPException(status_code=404, detail="No NDI preview frame available")
    return Response(
        content=frame.jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Frame-Captured-At": f"{frame.captured_at:.6f}",
        },
    )


@app.get("/api/anchor-photos/{anchor_name:path}")
async def get_anchor_photo(anchor_name: str, request: Request) -> FileResponse:
    mapping = mapping_store_from(request).load()
    path = await asyncio.to_thread(
        photo_resolver_from(request).photo_path_for,
        anchor_name,
        mapping.get("anchor_photos", {}),
    )
    if not path:
        raise HTTPException(status_code=404, detail="Anchor photo not found")
    return FileResponse(
        path,
        headers={
            "Cache-Control": "public, max-age=300",
        },
    )


@app.get("/api/diagnostics/qlxd")
async def get_qlxd_diagnostics(request: Request) -> dict:
    adapter = adapter_from(request)
    runtime_config = runtime_config_from(request)
    payload = {
        "source": runtime_config.source,
        "log_level": runtime_config.log_level,
        "log_file": str(runtime_config.log_file),
        "recent_logs": recent_logs(),
    }
    if hasattr(adapter, "diagnostics"):
        payload["runtime"] = adapter.diagnostics()
    else:
        payload["runtime"] = {"source": runtime_config.source, "receivers": []}
    return payload
