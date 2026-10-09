from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
import json
import logging
from zoneinfo import ZoneInfo

import requests


PROJECT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_EARTHQUAKES_PATH = PROJECT_DIR / "frontend" / "public" / "data" / "sample_earthquakes.json"

AFAD_LATEST_URL = "https://deprem.afad.gov.tr/apiv2/event/latest"
AFAD_FILTER_URL = "https://deprem.afad.gov.tr/apiv2/event/filter"
TURKEY_TIMEZONE = ZoneInfo("Europe/Istanbul")

logger = logging.getLogger("afad_service")


def fetch_json(url: str, timeout: int = 15) -> Any:
    """Fetch JSON from AFAD and log request details for debugging."""
    logger.info("AFAD request URL: %s", url)

    response = requests.get(
        url,
        headers={"User-Agent": "DepremKararDestekSistemi/1.0"},
        timeout=timeout,
    )
    logger.info("AFAD HTTP status code: %s", response.status_code)
    response.raise_for_status()

    try:
        return response.json()
    except ValueError as exc:
        logger.exception("AFAD JSON parse error: %s", exc)
        raise


def build_filter_url(start_time: datetime, end_time: datetime, limit: int = 500) -> str:
    """Build AFAD filter URL with the exact required datetime format."""
    query = urlencode(
        {
            "start": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "end": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "limit": limit,
            "orderby": "timedesc",
        }
    )
    return f"{AFAD_FILTER_URL}?{query}"


def today_range_turkey() -> tuple[datetime, datetime]:
    """Return today's 00:00:00-23:59:59 range in Turkey time."""
    now = datetime.now(TURKEY_TIMEZONE)
    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return start_time, end_time


def last_24_hours_range_turkey() -> tuple[datetime, datetime]:
    """Return the last 24 hours in Turkey time."""
    end_time = datetime.now(TURKEY_TIMEZONE).replace(microsecond=0)
    start_time = end_time - timedelta(hours=24)
    return start_time, end_time


def normalize_afad_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize AFAD or sample event fields into one frontend-friendly structure."""
    event_id = (
        event.get("eventID")
        or event.get("eventId")
        or event.get("earthquake_id")
        or event.get("id")
        or f"{event.get('date', '')}-{event.get('latitude', '')}-{event.get('longitude', '')}"
    )
    date = event.get("date") or event.get("eventDate") or event.get("time") or ""
    latitude = event.get("latitude", event.get("lat", 0))
    longitude = event.get("longitude", event.get("lon", event.get("lng", 0)))
    depth = event.get("depth", 0)
    magnitude = event.get("magnitude", event.get("mag", 0))
    location = event.get("location") or event.get("place") or "Konum bilgisi yok"

    return {
        "id": str(event_id),
        "date": str(date),
        "latitude": safe_float(latitude),
        "longitude": safe_float(longitude),
        "depth": safe_float(depth),
        "magnitude": safe_float(magnitude),
        "location": str(location),
        "source": event.get("source", "AFAD"),
    }


def safe_float(value: Any) -> float:
    """Convert values from external APIs without crashing on missing fields."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_events(payload: Any, source: str = "AFAD") -> list[dict[str, Any]]:
    """Normalize either a raw list or an object containing an event list."""
    if isinstance(payload, dict):
        raw_events = payload.get("data") or payload.get("events") or payload.get("result") or []
    elif isinstance(payload, list):
        raw_events = payload
    else:
        raw_events = []

    normalized = []
    for event in raw_events:
        if isinstance(event, dict):
            event = {**event, "source": source}
            normalized.append(normalize_afad_event(event))

    logger.info("AFAD normalized record count: %s", len(normalized))
    return normalized


def fetch_afad_today() -> list[dict[str, Any]]:
    """Fetch today's AFAD events from 00:00:00 to 23:59:59 Turkey time."""
    start_time, end_time = today_range_turkey()
    payload = fetch_json(build_filter_url(start_time, end_time))
    events = normalize_events(payload, source="AFAD")
    logger.info("AFAD today record count: %s", len(events))
    return events


def fetch_afad_last_24_hours() -> list[dict[str, Any]]:
    """Fetch AFAD events from the last 24 hours using the filter endpoint."""
    start_time, end_time = last_24_hours_range_turkey()
    payload = fetch_json(build_filter_url(start_time, end_time))
    events = normalize_events(payload, source="AFAD")
    logger.info("AFAD last 24 hours record count: %s", len(events))
    return events


def fetch_afad_latest() -> list[dict[str, Any]]:
    """Fetch latest AFAD events."""
    payload = fetch_json(AFAD_LATEST_URL)
    events = normalize_events(payload, source="AFAD")
    logger.info("AFAD latest record count: %s", len(events))
    return events


def get_sample_earthquakes() -> list[dict[str, Any]]:
    """Load bundled demo data when AFAD cannot be reached."""
    if not SAMPLE_EARTHQUAKES_PATH.exists():
        logger.error("Sample earthquake data not found: %s", SAMPLE_EARTHQUAKES_PATH)
        return []
    payload = json.loads(SAMPLE_EARTHQUAKES_PATH.read_text(encoding="utf-8"))
    events = normalize_events(payload, source="Demo")
    logger.info("Demo earthquake record count: %s", len(events))
    return events


def calculate_earthquake_statistics(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate dashboard statistics from normalized earthquake events."""
    if not events:
        return {
            "total": 0,
            "max_magnitude": None,
            "average_magnitude": None,
            "magnitude_four_plus": 0,
            "latest_time": None,
        }

    magnitudes = [safe_float(event.get("magnitude")) for event in events]
    latest_event = sorted(events, key=lambda event: str(event.get("date", "")), reverse=True)[0]

    return {
        "total": len(events),
        "max_magnitude": round(max(magnitudes), 1),
        "average_magnitude": round(sum(magnitudes) / len(magnitudes), 2),
        "magnitude_four_plus": len([value for value in magnitudes if value >= 4.0]),
        "latest_time": latest_event.get("date"),
    }
