"""Tests for the preprocessing playground API endpoints."""

import base64
import io

import pytest
from PIL import Image


def _make_png_data_url(width: int = 10, height: int = 10) -> str:
    """Create a tiny white PNG image encoded as a base64 data-URL."""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


async def test_list_steps(client):
    response = await client.get("/api/v1/preprocess/steps")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    names = [s["name"] for s in data]
    assert names == ["roi", "grayscale", "upscale", "denoise", "binarize"]
    roi = data[0]
    assert roi["label"] == "Region of Interest"
    assert any(p["name"] == "method" for p in roi["params"])


async def test_list_steps_has_param_descriptors(client):
    response = await client.get("/api/v1/preprocess/steps")
    binarize = [s for s in response.json() if s["name"] == "binarize"][0]
    method_param = [p for p in binarize["params"] if p["name"] == "method"][0]
    assert method_param["type"] == "select"
    assert method_param["default"] == "otsu"
    assert "otsu" in method_param["options"]
    assert "adaptive_gaussian" in method_param["options"]


async def test_preview_step_grayscale(client):
    data_url = _make_png_data_url()
    response = await client.post("/api/v1/preprocess/preview/step", json={
        "image": data_url,
        "step_name": "grayscale",
        "params": {},
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["step_name"] == "grayscale"
    assert data["image"].startswith("data:image/png;base64,")
    assert data["processing_time_ms"] >= 0


async def test_preview_step_with_params(client):
    data_url = _make_png_data_url()
    response = await client.post("/api/v1/preprocess/preview/step", json={
        "image": data_url,
        "step_name": "denoise",
        "params": {"method": "gaussian", "strength": "light"},
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["metadata"]["method"] == "gaussian"


async def test_preview_step_unknown_step(client):
    data_url = _make_png_data_url()
    response = await client.post("/api/v1/preprocess/preview/step", json={
        "image": data_url,
        "step_name": "nonexistent",
        "params": {},
    })
    assert response.status_code == 400


async def test_preview_step_invalid_image(client):
    response = await client.post("/api/v1/preprocess/preview/step", json={
        "image": "not-valid-base64",
        "step_name": "grayscale",
        "params": {},
    })
    assert response.status_code == 400


async def test_preview_pipeline_all_steps(client):
    data_url = _make_png_data_url()
    response = await client.post("/api/v1/preprocess/preview/pipeline", json={
        "image": data_url,
        "steps": {
            "roi": {"enabled": False},
            "grayscale": {},
            "upscale": {"method": "cubic", "scale_factor": 2},
            "denoise": {"method": "gaussian", "strength": "light"},
            "binarize": {"method": "otsu"},
        },
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["steps"]) == 5
    assert data["steps"][0]["enabled"] is False
    assert data["steps"][0]["image"] is None
    assert data["steps"][1]["enabled"] is True
    assert data["steps"][1]["success"] is True
    assert data["steps"][1]["image"] is not None
    assert data["total_processing_time_ms"] >= 0


async def test_preview_pipeline_disabled_steps(client):
    data_url = _make_png_data_url()
    response = await client.post("/api/v1/preprocess/preview/pipeline", json={
        "image": data_url,
        "steps": {
            "roi": {"enabled": False},
            "grayscale": {"enabled": False},
            "upscale": {"enabled": False},
            "denoise": {"enabled": False},
            "binarize": {"enabled": False},
        },
    })
    assert response.status_code == 200
    data = response.json()
    assert all(not s["enabled"] for s in data["steps"])
    assert all(s["image"] is None for s in data["steps"])


async def test_preview_pipeline_empty_config(client):
    data_url = _make_png_data_url()
    response = await client.post("/api/v1/preprocess/preview/pipeline", json={
        "image": data_url,
        "steps": {},
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["steps"]) == 5
    assert all(s["enabled"] for s in data["steps"])


async def test_export_pipeline(client):
    response = await client.post("/api/v1/preprocess/export", json={
        "steps": {
            "roi": {"method": "contour", "min_area": 500},
            "grayscale": {},
            "upscale": {"method": "cubic", "scale_factor": 2},
            "denoise": {"method": "gaussian", "strength": "light"},
            "binarize": {"method": "otsu", "invert": False},
        },
    })
    assert response.status_code == 200
    data = response.json()
    assert "yaml" in data
    yaml_str: str = data["yaml"]
    assert "preprocessing:" in yaml_str
    assert "enabled: true" in yaml_str
    assert "roi:" in yaml_str
    assert "binarize:" in yaml_str


async def test_export_pipeline_empty(client):
    response = await client.post("/api/v1/preprocess/export", json={
        "steps": {},
    })
    assert response.status_code == 200
    data = response.json()
    yaml_str = data["yaml"]
    assert "enabled: true" in yaml_str
    for name in ["roi", "grayscale", "upscale", "denoise", "binarize"]:
        assert f"{name}:" in yaml_str
