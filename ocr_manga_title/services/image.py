"""Image encoding/decoding utilities shared across routes and services."""

import base64
import tempfile
from io import BytesIO

import cv2
import numpy as np
from PIL import Image


def decode_image(data_url: str) -> np.ndarray:
    """Decode a base64 data-URL into an OpenCV BGR numpy array."""
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    raw = base64.b64decode(data_url)
    pil_img = Image.open(BytesIO(raw)).convert("RGB")
    return np.array(pil_img)[:, :, ::-1].copy()


def encode_image(image: np.ndarray) -> str:
    """Encode an OpenCV BGR numpy array into a base64 PNG data-URL."""
    if image.ndim == 2:
        pil_img = Image.fromarray(image)
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def decode_and_save(data_url: str) -> str:
    """Decode a base64 data-URL and save to a temp file. Returns the file path."""
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    raw = base64.b64decode(data_url)
    pil_img = Image.open(BytesIO(raw))
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    pil_img.save(tmp, format="PNG")
    tmp.close()
    return tmp.name


def numpy_to_temp_file(image: np.ndarray) -> str:
    """Save a numpy array as a temp PNG file. Returns the file path."""
    if image.ndim == 2:
        pil_img = Image.fromarray(image)
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    pil_img.save(tmp, format="PNG")
    tmp.close()
    return tmp.name
