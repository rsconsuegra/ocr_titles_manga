"""Unified OCR model registry — single source of truth for model descriptors and classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

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


def _build_registry() -> dict[str, ModelDescriptor]:
    from ocr_manga_title.engine.easyocr_model import EasyOCRModel
    from ocr_manga_title.engine.glm_ocr_model import GLMOCRModel
    from ocr_manga_title.engine.paddle_model import PaddleModel
    from ocr_manga_title.engine.tesseract_model import TesseractModel

    return {
        "tesseract": ModelDescriptor(
            name="tesseract",
            label="Tesseract",
            description="Open-source OCR engine via pytesseract. Supports multi-language and PSM/OEM modes.",
            model_cls=TesseractModel,
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
        ),
        "paddle": ModelDescriptor(
            name="paddle",
            label="PaddleOCR",
            description="Baidu's PaddleOCR engine. Supports multi-language text detection and recognition.",
            model_cls=PaddleModel,
            params=[
                ParamDescriptor(
                    name="languages",
                    type="text",
                    default="en+ja",
                    label="Languages",
                    description="Language codes (e.g. 'en+ja').",
                ),
            ],
        ),
        "easyocr": ModelDescriptor(
            name="easyocr",
            label="EasyOCR",
            description="Ready-to-use OCR with 80+ languages. PyTorch-based.",
            model_cls=EasyOCRModel,
            params=[
                ParamDescriptor(
                    name="languages",
                    type="text",
                    default="en+ja",
                    label="Languages",
                    description="Language codes (e.g. 'en+ja').",
                ),
            ],
        ),
        "glm_ocr": ModelDescriptor(
            name="glm_ocr",
            label="GLM-OCR",
            description="Vision-language model for OCR via API endpoint.",
            model_cls=GLMOCRModel,
            params=[
                ParamDescriptor(
                    name="api_endpoint",
                    type="text",
                    default="",
                    label="API Endpoint",
                    description="URL of the GLM-OCR API service.",
                ),
            ],
        ),
    }


MODEL_REGISTRY: dict[str, ModelDescriptor] = _build_registry()


def get_all_models() -> list[ModelDescriptor]:
    """Return all model descriptors in registry order."""
    return list(MODEL_REGISTRY.values())


def get_model(name: str) -> ModelDescriptor | None:
    """Return a single model descriptor by name, or ``None``."""
    return MODEL_REGISTRY.get(name)
