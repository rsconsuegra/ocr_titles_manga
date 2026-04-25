"""Unified OCR model registry — single source of truth for model descriptors and classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ocr_manga_title.preprocess.registry import ParamDescriptor

if TYPE_CHECKING:
    from ocr_manga_title.engine.base import BaseOCRModel


@dataclass(frozen=True)
class ModelDescriptor:
    """Static descriptor for an OCR model."""

    name: str
    label: str
    description: str
    model_cls: type[BaseOCRModel]
    params: list[ParamDescriptor] = field(default_factory=list)


def _build_tesseract(model_cls: type[BaseOCRModel]) -> ModelDescriptor:
    return ModelDescriptor(
        name="tesseract",
        label="Tesseract",
        description="Open-source OCR engine via pytesseract. Supports multi-language and PSM/OEM modes.",
        model_cls=model_cls,
        params=[
            ParamDescriptor(
                name="languages",
                type="multiselect",
                default=["eng", "jpn"],
                label="Languages",
                description="Select one or more languages. Multiple languages are joined with '+'.",
                options=[
                    "eng",
                    "jpn",
                    "chi_sim",
                    "kor",
                    "spa",
                    "fra",
                    "deu",
                    "por",
                    "ita",
                ],
            ),
            ParamDescriptor(
                name="psm",
                type="number",
                default=3,
                label="Page Segmentation Mode",
                description="Tesseract PSM value (0-13).",
                min=0,
                max=13,
                step=1,
            ),
            ParamDescriptor(
                name="oem",
                type="number",
                default=3,
                label="OCR Engine Mode",
                description="Tesseract OEM value (0-3).",
                min=0,
                max=3,
                step=1,
            ),
        ],
    )


def _build_paddle(model_cls: type[BaseOCRModel]) -> ModelDescriptor:
    return ModelDescriptor(
        name="paddle",
        label="PaddleOCR",
        description="Baidu's PaddleOCR engine with multilingual support and GPU acceleration.",
        model_cls=model_cls,
        params=[
            ParamDescriptor(
                name="languages",
                type="multiselect",
                default=["en", "ja"],
                label="Languages",
                description="OCR languages.",
                options=["en", "ja", "ch", "ko", "spa", "fra", "deu", "por", "ita"],
            ),
            ParamDescriptor(
                name="use_gpu",
                type="boolean",
                default=False,
                label="Use GPU",
                description="Enable CUDA acceleration.",
            ),
        ],
    )


def _build_easyocr(model_cls: type[BaseOCRModel]) -> ModelDescriptor:
    return ModelDescriptor(
        name="easyocr",
        label="EasyOCR",
        description="PyTorch-based OCR with 80+ languages and GPU acceleration.",
        model_cls=model_cls,
        params=[
            ParamDescriptor(
                name="languages",
                type="multiselect",
                default=["en", "ja"],
                label="Languages",
                description="OCR languages.",
                options=[
                    "en",
                    "ja",
                    "ch_sim",
                    "ch_tra",
                    "ko",
                    "es",
                    "fr",
                    "de",
                    "pt",
                    "it",
                ],
            ),
            ParamDescriptor(
                name="gpu",
                type="boolean",
                default=False,
                label="Use GPU",
                description="Enable CUDA acceleration.",
            ),
        ],
    )


def _build_glm_ocr(model_cls: type[BaseOCRModel]) -> ModelDescriptor:
    return ModelDescriptor(
        name="glm_ocr",
        label="Vision API (GLM OCR)",
        description="Generic vision-language model OCR via OpenAI-compatible API.",
        model_cls=model_cls,
        params=[
            ParamDescriptor(
                name="api_endpoint",
                type="text",
                default="",
                label="API Endpoint",
                description="Vision API base URL (e.g. https://openrouter.ai/api/v1).",
            ),
            ParamDescriptor(
                name="model",
                type="text",
                default="google/gemini-2.5-flash",
                label="Model",
                description="Vision model identifier at the endpoint.",
            ),
            ParamDescriptor(
                name="api_key",
                type="text",
                default="",
                label="API Key",
                description="API key (leave empty to use OpenRouter key from config).",
            ),
            ParamDescriptor(
                name="prompt",
                type="text",
                default="Extract all text from this image.",
                label="Extraction Prompt",
                description="Text prompt sent with the image.",
            ),
        ],
    )


def _build_registry() -> dict[str, ModelDescriptor]:
    from ocr_manga_title.engine.easyocr_model import EasyOCRModel
    from ocr_manga_title.engine.glm_ocr_model import GLMOCRModel
    from ocr_manga_title.engine.paddle_model import PaddleModel
    from ocr_manga_title.engine.tesseract_model import TesseractModel

    return {
        "tesseract": _build_tesseract(TesseractModel),
        "paddle": _build_paddle(PaddleModel),
        "easyocr": _build_easyocr(EasyOCRModel),
        "glm_ocr": _build_glm_ocr(GLMOCRModel),
    }


MODEL_REGISTRY: dict[str, ModelDescriptor] = _build_registry()


def get_all_models() -> list[ModelDescriptor]:
    """Return all model descriptors in registry order."""
    return list(MODEL_REGISTRY.values())


def get_model(name: str) -> ModelDescriptor | None:
    """Return a single model descriptor by name, or ``None``."""
    return MODEL_REGISTRY.get(name)
