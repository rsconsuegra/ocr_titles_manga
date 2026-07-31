"""Image encoding/decoding utilities shared across routes and services."""

import atexit
import base64
import tempfile
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from fastapi import UploadFile
from PIL import Image

_temp_files: list[str] = []


def _cleanup_temp_files() -> None:
    for path in _temp_files:
        Path(path).unlink(missing_ok=True)


atexit.register(_cleanup_temp_files)


def _create_temp_file(suffix: str = ".png") -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        name = tmp.name
    _temp_files.append(name)
    return name


def _bytes_to_bgr(raw: bytes) -> np.ndarray:
    pil_img = Image.open(BytesIO(raw)).convert("RGB")
    return np.array(pil_img)[:, :, ::-1].copy()


def _bytes_to_temp(raw: bytes) -> str:
    pil_img = Image.open(BytesIO(raw))
    tmp_path = _create_temp_file()
    pil_img.save(tmp_path, format="PNG")
    return tmp_path


def _to_pil(image: np.ndarray) -> Image.Image:
    if image.ndim == 2:
        return Image.fromarray(image)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def decode_image(data_url: str) -> np.ndarray:
    """Decode a base64 data-URL into an OpenCV BGR numpy array."""
    from ocr_manga_title.settings import MAX_FILE_SIZE

    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    if len(data_url) > MAX_FILE_SIZE * 2:
        raise ValueError(
            f"Image data exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit"
        )
    return _bytes_to_bgr(base64.b64decode(data_url))


async def decode_upload(file: UploadFile) -> np.ndarray:
    """Decode an uploaded file into an OpenCV BGR numpy array."""
    return _bytes_to_bgr(await file.read())


def encode_image(image: np.ndarray) -> str:
    """Encode an OpenCV BGR numpy array into a base64 PNG data-URL."""
    buf = BytesIO()
    _to_pil(image).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def decode_and_save(data_url: str) -> str:
    """Decode a base64 data-URL and save to a temp file. Returns the file path."""
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    return _bytes_to_temp(base64.b64decode(data_url))


async def save_upload(file: UploadFile) -> str:
    """Read an uploaded file and save to a temp file. Returns the file path."""
    return _bytes_to_temp(await file.read())


def save_bytes(raw: bytes) -> str:
    """Save raw image bytes to a temp PNG file. Returns the file path."""
    return _bytes_to_temp(raw)


def decode_bytes(raw: bytes) -> np.ndarray:
    """Decode raw image bytes into an OpenCV BGR numpy array."""
    return _bytes_to_bgr(raw)


def numpy_to_temp_file(image: np.ndarray) -> str:
    """Save a numpy array as a temp PNG file. Returns the file path."""
    tmp_path = _create_temp_file()
    _to_pil(image).save(tmp_path, format="PNG")
    return tmp_path
