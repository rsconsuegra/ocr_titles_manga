"""Tests for the OCR playground API endpoints."""

import base64
import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from ocr_manga_title.api.schemas.ocr import LLMResultData, OCRResultData


def _make_png_data_url(width: int = 10, height: int = 10) -> str:
    img = Image.new("RGB", (width, height), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


async def test_list_ocr_registry(client):
    response = await client.get("/api/v1/ocr/registry")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    names = [m["name"] for m in data]
    assert "tesseract" in names
    assert "paddle" in names
    assert "easyocr" in names
    assert "glm_ocr" in names


async def test_list_ocr_registry_has_params(client):
    response = await client.get("/api/v1/ocr/registry")
    tess = [m for m in response.json() if m["name"] == "tesseract"][0]
    param_names = [p["name"] for p in tess["params"]]
    assert "languages" in param_names
    assert "psm" in param_names
    assert "oem" in param_names


async def test_list_ocr_registry_has_enabled_flag(client):
    response = await client.get("/api/v1/ocr/registry")
    data = response.json()
    for m in data:
        assert "enabled" in m
        assert "available" in m


async def test_run_ocr_unknown_model(client):
    response = await client.post(
        "/api/v1/ocr/run",
        json={"image": _make_png_data_url(), "model_name": "nonexistent"},
    )
    assert response.status_code == 400
    assert "Unknown model" in response.json()["detail"]


async def test_run_ocr_invalid_image(client):
    response = await client.post(
        "/api/v1/ocr/run",
        json={"image": "not-a-valid-image", "model_name": "tesseract"},
    )
    assert response.status_code == 400


async def test_run_ocr_tesseract_success(client):
    mock_result = OCRResultData(
        raw_text="Test Manga Title",
        model_name="tesseract",
        confidence=0.92,
        processing_time_ms=150,
    )
    with patch("ocr_manga_title.api.routes.ocr.run_single_model", return_value=mock_result):
        response = await client.post(
            "/api/v1/ocr/run",
            json={"image": _make_png_data_url(), "model_name": "tesseract"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ocr"]["raw_text"] == "Test Manga Title"
    assert data["ocr"]["confidence"] == 0.92
    assert data["llm"] is None


async def test_run_ocr_with_llm(client):
    mock_ocr = OCRResultData(
        raw_text="One Piece",
        model_name="tesseract",
        confidence=0.85,
        processing_time_ms=100,
    )
    mock_llm = LLMResultData(
        title_en="One Piece",
        code="OP",
        confidence=0.9,
        source_method="llm",
    )

    with patch("ocr_manga_title.api.routes.ocr.run_single_model", return_value=mock_ocr), \
         patch("ocr_manga_title.api.routes.ocr.run_llm_extraction", return_value=mock_llm):
        response = await client.post(
            "/api/v1/ocr/run",
            json={
                "image": _make_png_data_url(),
                "model_name": "tesseract",
                "enable_llm": True,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ocr"]["raw_text"] == "One Piece"
    assert data["llm"] is not None
    assert data["llm"]["title_en"] == "One Piece"


async def test_run_ocr_model_not_available(client):
    mock_result = OCRResultData(
        model_name="paddle",
        error="Model not available",
    )
    with patch("ocr_manga_title.api.routes.ocr.run_single_model", return_value=mock_result):
        response = await client.post(
            "/api/v1/ocr/run",
            json={"image": _make_png_data_url(), "model_name": "paddle"},
        )

    assert response.status_code == 400
    assert "not available" in response.json()["detail"]


async def test_run_ocr_model_run_error(client):
    mock_result = OCRResultData(
        model_name="tesseract",
        error="OCR crashed",
        confidence=0.0,
        processing_time_ms=50,
    )
    with patch("ocr_manga_title.api.routes.ocr.run_single_model", return_value=mock_result):
        response = await client.post(
            "/api/v1/ocr/run",
            json={"image": _make_png_data_url(), "model_name": "tesseract"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ocr"]["error"] == "OCR crashed"
    assert data["ocr"]["confidence"] == 0.0


async def test_export_ocr_config(client):
    response = await client.post(
        "/api/v1/ocr/export",
        json={"models": {"tesseract": {"enabled": True}}},
    )
    assert response.status_code == 200
    import yaml
    data = yaml.safe_load(response.json()["yaml"])
    assert "models" in data
    assert "tesseract" in data["models"]
    assert data["models"]["tesseract"]["enabled"] is True


async def test_export_ocr_config_splits_languages(client):
    response = await client.post(
        "/api/v1/ocr/export",
        json={"models": {"tesseract": {"languages": "eng+jpn"}}},
    )
    assert response.status_code == 200
    import yaml
    data = yaml.safe_load(response.json()["yaml"])
    tess = data["models"]["tesseract"]
    assert tess["languages"] == ["eng", "jpn"]
