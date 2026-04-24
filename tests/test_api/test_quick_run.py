"""Tests for the quick-run API endpoint."""

import base64
import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from ocr_manga_title.api.schemas.ocr import OCRResultData


def _make_png_data_url(width: int = 10, height: int = 10) -> str:
    img = Image.new("RGB", (width, height), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


async def test_quick_run_no_models(client):
    response = await client.post(
        "/api/v1/run/quick",
        json={"image": _make_png_data_url(), "ocr_models": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ocr_results"] == []
    assert data["llm"] is None


async def test_quick_run_with_tesseract(client):
    mock_results = [OCRResultData(
        raw_text="Naruto",
        model_name="tesseract",
        confidence=0.88,
        processing_time_ms=200,
    )]
    with patch("ocr_manga_title.api.routes.run.run_all_enabled_models", return_value=mock_results):
        response = await client.post(
            "/api/v1/run/quick",
            json={
                "image": _make_png_data_url(),
                "ocr_models": {"tesseract": {"enabled": True}},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["ocr_results"]) == 1
    assert data["ocr_results"][0]["raw_text"] == "Naruto"
    assert data["total_processing_time_ms"] >= 0


async def test_quick_run_with_preprocessing(client):
    mock_results = [OCRResultData(
        raw_text="Bleach",
        model_name="tesseract",
        confidence=0.75,
        processing_time_ms=100,
    )]
    with patch("ocr_manga_title.api.routes.run.run_all_enabled_models", return_value=mock_results), \
         patch("ocr_manga_title.api.routes.run.run_preprocessing_pipeline", return_value="/tmp/test.png"):
        response = await client.post(
            "/api/v1/run/quick",
            json={
                "image": _make_png_data_url(),
                "preprocess_steps": {"grayscale": {"enabled": True}},
                "ocr_models": {"tesseract": {"enabled": True}},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["ocr_results"]) == 1
    assert data["ocr_results"][0]["raw_text"] == "Bleach"


async def test_quick_run_with_llm(client):
    from ocr_manga_title.api.schemas.ocr import LLMResultData

    mock_results = [OCRResultData(
        raw_text="Death Note",
        model_name="tesseract",
        confidence=0.9,
        processing_time_ms=50,
    )]
    mock_llm = LLMResultData(
        title_en="Death Note",
        code="DN",
        confidence=0.95,
        source_method="llm",
    )

    with patch("ocr_manga_title.api.routes.run.run_all_enabled_models", return_value=mock_results), \
         patch("ocr_manga_title.api.routes.run.run_llm_extraction", return_value=mock_llm):
        response = await client.post(
            "/api/v1/run/quick",
            json={
                "image": _make_png_data_url(),
                "ocr_models": {"tesseract": {"enabled": True}},
                "enable_llm": True,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["llm"] is not None
    assert data["llm"]["title_en"] == "Death Note"


async def test_quick_run_model_not_available(client):
    mock_results = [OCRResultData(
        model_name="paddle",
        error="Model not available",
    )]
    with patch("ocr_manga_title.api.routes.run.run_all_enabled_models", return_value=mock_results):
        response = await client.post(
            "/api/v1/run/quick",
            json={
                "image": _make_png_data_url(),
                "ocr_models": {"paddle": {"enabled": True}},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["ocr_results"]) == 1
    assert "not available" in data["ocr_results"][0]["error"]


async def test_quick_run_invalid_image(client):
    response = await client.post(
        "/api/v1/run/quick",
        json={"image": "garbage", "ocr_models": {}},
    )
    assert response.status_code == 400
