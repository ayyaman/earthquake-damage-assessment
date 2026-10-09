from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal
import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from predict import predict_image
from regional_analysis import HEATMAPS_DIR, OUTPUTS_DIR, analyze_regional_pair, generate_change_heatmap
from risk_analysis import analyze_risk
from services.afad_service import (
    calculate_earthquake_statistics,
    fetch_afad_last_24_hours,
    fetch_afad_latest,
    fetch_afad_today,
    get_sample_earthquakes,
)


PROJECT_DIR = Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Earthquake Decision Support API",
    description="Building damage classification, risk analysis and regional prioritization.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")


class RiskAnalysisRequest(BaseModel):
    damage_level: Literal["no_damage", "damaged", "collapsed"]
    time_of_day: Literal["day", "night"]
    building_type: Literal["residential", "office", "school", "hospital", "shopping_mall"]
    occupancy_range: Literal["auto", "low", "medium", "high"] = "auto"


def save_upload_to_temp_file(upload: UploadFile) -> Path:
    """Save an uploaded file temporarily so existing image utilities can read it."""
    suffix = Path(upload.filename or "upload.jpg").suffix or ".jpg"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(upload.file.read())
        return Path(temp_file.name)


@app.get("/")
def api_status() -> dict[str, str]:
    return {"status": "Earthquake Decision Support API is running"}


@app.get("/earthquakes/latest")
def get_latest_earthquakes() -> dict:
    try:
        events = fetch_afad_latest()
        if not events:
            raise RuntimeError("AFAD latest returned no events.")
        source = "AFAD Canlı Veri"
        error = None
    except Exception:
        events = get_sample_earthquakes()
        source = "Demo Veri"
        error = "AFAD canlı verisine ulaşılamadığı için demo veri gösterilmektedir."

    return {
        "earthquakes": events,
        "source": source,
        "recordCount": len(events),
        "lastUpdated": datetime_now_text(),
        "error": error,
        "statistics": calculate_earthquake_statistics(events),
    }


@app.get("/earthquakes/test-afad")
def test_afad_connection() -> dict:
    try:
        events = fetch_afad_latest()
        return {
            "success": True,
            "source": "AFAD Canlı Veri",
            "recordCount": len(events),
            "lastUpdated": datetime_now_text(),
        }
    except Exception as exc:
        import logging

        logging.getLogger("afad_service").exception("AFAD test endpoint error: %s", exc)
        return {
            "success": False,
            "source": "AFAD Canlı Veri",
            "recordCount": 0,
            "lastUpdated": datetime_now_text(),
            "error": "AFAD canlı verisine ulaşılamadı.",
        }


@app.get("/earthquakes/today")
def get_today_earthquakes() -> dict:
    try:
        events = fetch_afad_today()
        if not events:
            raise RuntimeError("AFAD today returned no events.")
        source = "AFAD Canlı Veri"
        error = None
    except Exception as today_error:
        import logging

        logging.getLogger("afad_service").exception("AFAD today endpoint error: %s", today_error)
        try:
            events = fetch_afad_latest()
            if not events:
                raise RuntimeError("AFAD latest returned no events.")
            source = "AFAD Canlı Veri"
            error = "Bugünün filtreli verisi alınamadı; AFAD son depremler verisi gösterilmektedir."
        except Exception as latest_error:
            logging.getLogger("afad_service").exception("AFAD latest fallback error: %s", latest_error)
            events = get_sample_earthquakes()
            source = "Demo Veri"
            error = "AFAD canlı verisine ulaşılamadığı için demo veri gösterilmektedir."

    return {
        "earthquakes": events,
        "source": source,
        "recordCount": len(events),
        "lastUpdated": datetime_now_text(),
        "error": error,
        "statistics": calculate_earthquake_statistics(events),
    }


@app.get("/earthquakes/last-24-hours")
def get_last_24_hours_earthquakes() -> dict:
    try:
        events = fetch_afad_last_24_hours()
        if not events:
            raise RuntimeError("AFAD filter returned no events.")
        source = "AFAD Canlı Veri"
        error = None
    except Exception:
        try:
            events = fetch_afad_latest()
            if not events:
                raise RuntimeError("AFAD latest returned no events.")
            source = "AFAD Canlı Veri"
            error = "AFAD son 24 saat filtresi kullanılamadı; son depremler verisi gösterilmektedir."
        except Exception:
            events = get_sample_earthquakes()
            source = "Demo Veri"
            error = "AFAD canlı verisine ulaşılamadığı için demo veri gösterilmektedir."

    return {
        "earthquakes": events,
        "source": source,
        "recordCount": len(events),
        "lastUpdated": datetime_now_text(),
        "error": error,
        "statistics": calculate_earthquake_statistics(events),
    }


def datetime_now_text() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%d.%m.%Y %H:%M")


@app.post("/predict-building-damage")
def predict_building_damage(image: UploadFile = File(...)) -> dict:
    temp_path = save_upload_to_temp_file(image)
    try:
        result = predict_image(temp_path)
        result["damage_level"] = result["predicted_class"]
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)


@app.post("/risk-analysis")
def run_risk_analysis(request: RiskAnalysisRequest) -> dict:
    try:
        return analyze_risk(
            damage_level=request.damage_level,
            time_of_day=request.time_of_day,
            building_type=request.building_type,
            occupancy_range=request.occupancy_range,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/predict-regional-damage")
def predict_regional_damage(
    pre_image: UploadFile = File(...),
    post_image: UploadFile = File(...),
) -> dict:
    pre_path = save_upload_to_temp_file(pre_image)
    post_path = save_upload_to_temp_file(post_image)

    try:
        result = analyze_regional_pair(pre_path, post_path)
        heatmap_name = f"api_{pre_path.stem}_heatmap.png"
        heatmap_path = generate_change_heatmap(pre_path, post_path, HEATMAPS_DIR / heatmap_name)
        result["heatmap_path"] = str(heatmap_path)
        result["heatmap_url"] = f"/outputs/regional_heatmaps/{heatmap_path.name}"
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        pre_path.unlink(missing_ok=True)
        post_path.unlink(missing_ok=True)
