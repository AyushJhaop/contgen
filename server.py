import json
import os
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from automation_pipeline import (
    run_full_automation_pipeline,
    stage_3_build_canva_and_webhook_mapping,
    SlideSpec,
    BrandKit,
    PRESET_IDEAS,
    PAYLOAD_PATH,
)
from render_slides import render_carousel_from_payload, THEMES, BASE_DIR, SLIDES_DIR, EXPORTS_DIR

app = FastAPI(title="Founder AI Carousel Automation API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(SLIDES_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

app.mount("/slides", StaticFiles(directory=SLIDES_DIR), name="slides")
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")


class RunPipelineRequest(BaseModel):
    raw_idea: str
    theme_id: str = "obsidian_slate"
    aspect_ratio: str = "4:5 (1080x1350)"
    handle: str = "@founder.playbook"


class UpdateCarouselRequest(BaseModel):
    payload: Dict[str, Any]


def _load_or_init_payload() -> Dict[str, Any]:
    if os.path.exists(PAYLOAD_PATH):
        with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "slides" in data and "research_brief" in data:
            return data
    return run_full_automation_pipeline(PRESET_IDEAS[0]["raw_idea"])


@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    payload = _load_or_init_payload()
    themes_list = [{"id": k, "name": v["name"]} for k, v in THEMES.items()]
    return {
        "payload": payload,
        "themes": themes_list,
        "presets": PRESET_IDEAS,
        "timestamp": int(time.time() * 1000),
    }


@app.post("/api/pipeline/run")
def api_run_pipeline(req: RunPipelineRequest) -> Dict[str, Any]:
    payload = run_full_automation_pipeline(
        raw_idea=req.raw_idea,
        theme_id=req.theme_id,
        aspect_ratio=req.aspect_ratio,
        handle=req.handle,
    )
    return {
        "payload": payload,
        "timestamp": int(time.time() * 1000),
    }


@app.post("/api/slides/update")
def api_update_slides(req: UpdateCarouselRequest) -> Dict[str, Any]:
    t0 = time.time()
    payload = req.payload
    brand_raw = payload.get("brand_kit", {})
    theme_id = brand_raw.get("theme_id", "obsidian_slate")
    theme_meta = THEMES.get(theme_id, THEMES["obsidian_slate"])
    brand_kit = BrandKit(
        theme_id=theme_id,
        theme_name=theme_meta["name"],
        handle=brand_raw.get("handle", "@founder.playbook"),
    )
    payload["brand_kit"] = brand_kit.model_dump()

    validated_slides = [SlideSpec(**s) for s in payload.get("slides", [])]
    payload["slides"] = [s.model_dump() for s in validated_slides]
    payload["canva_autofill_mapping"] = stage_3_build_canva_and_webhook_mapping(
        validated_slides, brand_kit
    )

    assets = render_carousel_from_payload(payload)
    payload["assets"] = assets

    logs = payload.get("pipeline_logs", [])
    logs.append(
        {
            "stage": "Live Re-Render (Founder Edit)",
            "engine": f"Pillow 1080p Renderer ({assets['dimensions']})",
            "duration_ms": int((time.time() - t0) * 1000),
            "summary": f"Updated {assets['slide_count']} PNGs, LinkedIn PDF & Instagram ZIP.",
        }
    )
    payload["pipeline_logs"] = logs[-8:]

    with open(PAYLOAD_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return {
        "payload": payload,
        "timestamp": int(time.time() * 1000),
    }


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

