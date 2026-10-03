import asyncio
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from config import APP_SECRET, GRAPH_VERSION, PAGE_ACCESS_TOKEN

log = logging.getLogger("meta")


def verify_signature(raw_body: bytes, header: Optional[str]) -> bool:
    """Validate X-Hub-Signature-256 sent by Meta on webhook POSTs."""
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def _appsecret_proof() -> str:
    return hmac.new(APP_SECRET.encode(), PAGE_ACCESS_TOKEN.encode(), hashlib.sha256).hexdigest()


async def fetch_lead(leadgen_id: str, attempts: int = 3) -> dict[str, Any]:
    """GET /{leadgen_id} from the Graph API. Retries briefly on transient failures."""
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{leadgen_id}"
    params = {"access_token": PAGE_ACCESS_TOKEN, "appsecret_proof": _appsecret_proof()}
    last_exc: Optional[Exception] = None
    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(1, attempts + 1):
            try:
                resp = await client.get(url, params=params)
                if resp.status_code < 400:
                    return resp.json()
                log.warning("Graph API %s: %s", resp.status_code, resp.text)
                # 4xx other than rate-limit won't fix themselves
                if resp.status_code < 500 and resp.status_code != 429:
                    resp.raise_for_status()
                last_exc = httpx.HTTPStatusError("graph error", request=resp.request, response=resp)
            except httpx.TransportError as exc:
                last_exc = exc
            await asyncio.sleep(2 * attempt)
    raise RuntimeError(f"Could not fetch lead {leadgen_id}") from last_exc


def parse_lead(graph_lead: dict[str, Any]) -> dict[str, Optional[str]]:
    """Flatten Meta's field_data list into name / email / phone."""
    fields: dict[str, str] = {}
    for item in graph_lead.get("field_data", []):
        values = item.get("values") or []
        if values:
            fields[item.get("name", "").lower()] = str(values[0])

    name = fields.get("full_name")
    if not name:
        parts = [fields.get("first_name"), fields.get("last_name")]
        name = " ".join(p for p in parts if p) or None

    return {
        "name": name,
        "email": fields.get("email"),
        "phone": fields.get("phone_number") or fields.get("phone"),
    }


def normalize_time(value: Optional[str]) -> str:
    """Meta sends e.g. 2026-09-28T10:00:00+0000; convert to strict ISO-8601 (JS/Hermes friendly)."""
    if value:
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").isoformat()
        except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat()
