import json
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse

import db
from config import VERIFY_TOKEN
from meta import fetch_lead, normalize_time, parse_lead, verify_signature
from ws_manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

db.init_db()
app = FastAPI(title="Meta Lead Ads PoC")


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/leads")
async def get_leads(limit: int = Query(100, ge=1, le=500)):
    return await run_in_threadpool(db.list_leads, limit)


# ---------- Meta webhook ----------

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
):
    """Meta calls this once when you save the webhook in the App Dashboard."""
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(raw)
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "leadgen":
                background.add_task(process_lead, change.get("value", {}))

    # Respond 200 fast; Meta retries if we are slow.
    return {"status": "ok"}


async def process_lead(value: dict) -> None:
    leadgen_id = value.get("leadgen_id")
    if not leadgen_id:
        log.warning("leadgen event without leadgen_id: %s", value)
        return
    try:
        graph_lead = await fetch_lead(str(leadgen_id))
        parsed = parse_lead(graph_lead)
        stored = await run_in_threadpool(
            lambda: db.insert_lead(
                meta_lead_id=str(leadgen_id),
                name=parsed["name"],
                email=parsed["email"],
                phone=parsed["phone"],
                form_id=str(value.get("form_id") or graph_lead.get("form_id") or "") or None,
                page_id=str(value.get("page_id") or "") or None,
                created_time=normalize_time(graph_lead.get("created_time") or None),
                raw=graph_lead,
            )
        )
        if stored is None:
            log.info("Duplicate lead %s ignored", leadgen_id)
            return
        log.info("Stored lead %s", leadgen_id)
        await manager.broadcast({"type": "lead", "data": stored})
    except Exception:
        log.exception("Failed processing lead %s", leadgen_id)


# ---------- WebSocket ----------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # we only push; this detects disconnects
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
