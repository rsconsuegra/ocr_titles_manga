"""Unified OCR model registry — single source of truth for model descriptors and classes."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ocr_manga_title.preprocess.registry import ParamDescriptor

if TYPE_CHECKING:
    from ocr_manga_title.engine.base import BaseOCRModel


class _LazyModelClass:
    """Proxy that defers model-class import until first attribute access."""

    def __init__(self, dotted_path: str) -> None:
        self._dotted_path = dotted_path
        self._resolved: type[BaseOCRModel] | None = None

    def _resolve(self) -> type[BaseOCRModel]:
        if self._resolved is None:
            module_path, _, class_name = self._dotted_path.rpartition(".")
            mod = importlib.import_module(module_path)
            self._resolved = getattr(mod, class_name)
        return self._resolved

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._resolve()(*args, **kwargs)

    def __instancecheck__(self, instance: Any) -> bool:
        return isinstance(instance, self._resolve())

    def __subclasscheck__(self, subclass: Any) -> bool:
        return issubclass(subclass, self._resolve())

    def __repr__(self) -> str:
        if self._resolved is not None:
            return repr(self._resolved)
        return f"<lazy {self._dotted_path}>"


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
            ParamDescriptor(
                name="detailed",
                type="boolean",
                default=False,
                label="Detailed",
                description="Return bounding boxes and per-block details.",
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
            ParamDescriptor(
                name="detailed",
                type="boolean",
                default=False,
                label="Detailed",
                description="Return bounding boxes and per-block details.",
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
            ParamDescriptor(
                name="paragraph",
                type="boolean",
                default=False,
                label="Paragraph",
                description="Combine detected text into paragraphs.",
            ),
            ParamDescriptor(
                name="detailed",
                type="boolean",
                default=False,
                label="Detailed",
                description="Return bounding boxes and per-block details.",
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


def _build_ollama_vision(model_cls: type[BaseOCRModel]) -> ModelDescriptor:
    return ModelDescriptor(
        name="ollama_vision",
        label="Ollama Vision",
        description="Ollama multimodal model for OCR via native /api/chat endpoint. Model selection is dynamic.",
        model_cls=model_cls,
        params=[
            ParamDescriptor(
                name="prompt",
                type="textarea",
                default="Extract all text from this image.",
                label="Extraction Prompt",
                description="Instructions sent to the vision model with the image.",
            ),
            ParamDescriptor(
                name="temperature",
                type="number",
                default=0.1,
                label="Temperature",
                description="Sampling temperature.",
                min=0.0,
                max=2.0,
                step=0.1,
            ),
        ],
    )


def _build_registry() -> dict[str, ModelDescriptor]:
    return {
        "tesseract": _build_tesseract(
            _LazyModelClass("ocr_manga_title.engine.tesseract_model.TesseractModel")  # type: ignore[arg-type]
        ),
        "paddle": _build_paddle(
            _LazyModelClass("ocr_manga_title.engine.paddle_model.PaddleModel")  # type: ignore[arg-type]
        ),
        "easyocr": _build_easyocr(
            _LazyModelClass("ocr_manga_title.engine.easyocr_model.EasyOCRModel")  # type: ignore[arg-type]
        ),
        "glm_ocr": _build_glm_ocr(
            _LazyModelClass("ocr_manga_title.engine.glm_ocr_model.GLMOCRModel")  # type: ignore[arg-type]
        ),
        "ollama_vision": _build_ollama_vision(
            _LazyModelClass(  # type: ignore[arg-type]
                "ocr_manga_title.engine.ollama_vision_model.OllamaVisionModel"
            )
        ),
    }


MODEL_REGISTRY: dict[str, ModelDescriptor] = _build_registry()


def registry_defaults(descriptor: ModelDescriptor) -> dict[str, Any]:
    """Return ``{param.name: param.default}`` for every param in *descriptor*."""
    return {p.name: p.default for p in descriptor.params}


def get_model(name: str) -> ModelDescriptor | None:
    """Return a single model descriptor by name, or ``None``."""
    return MODEL_REGISTRY.get(name)
