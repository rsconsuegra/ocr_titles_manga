"""Step registry — static descriptors for every preprocessing step."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParamDescriptor:
    """Schema for a single parameter exposed by a preprocessing step."""

    name: str
    type: str
    default: Any
    label: str = ""
    description: str = ""
    options: list[str] | None = None
    disabled_options: dict[str, str] = field(default_factory=dict)
    min: float | None = None
    max: float | None = None
    step: float | None = None


@dataclass(frozen=True)
class StepDescriptor:
    """Static descriptor for a preprocessing step."""

    name: str
    label: str
    description: str
    params: list[ParamDescriptor] = field(default_factory=list)


STEP_REGISTRY: dict[str, StepDescriptor] = {
    "roi": StepDescriptor(
        name="roi",
        label="Region of Interest",
        description="Detects and crops the region of interest using contour detection.",
        params=[
            ParamDescriptor(
                name="method",
                type="select",
                default="contour",
                label="Detection Method",
                options=["contour"],
            ),
            ParamDescriptor(
                name="min_area",
                type="number",
                default=500,
                label="Min Area",
                description="Minimum contour area to consider.",
                min=0,
                step=50,
            ),
            ParamDescriptor(
                name="padding",
                type="number",
                default=10,
                label="Padding",
                description="Pixels of padding around the detected region.",
                min=0,
                step=1,
            ),
            ParamDescriptor(
                name="merge_overlap",
                type="number",
                default=0.3,
                label="Merge Overlap (IoU)",
                description="IoU threshold for merging overlapping regions.",
                min=0.0,
                max=1.0,
                step=0.05,
            ),
        ],
    ),
    "grayscale": StepDescriptor(
        name="grayscale",
        label="Grayscale",
        description="Converts BGR/BGRA images to single-channel grayscale.",
        params=[],
    ),
    "upscale": StepDescriptor(
        name="upscale",
        label="Upscale",
        description="Upscales images using cubic interpolation or DNN super-resolution.",
        params=[
            ParamDescriptor(
                name="method",
                type="select",
                default="cubic",
                label="Method",
                options=["cubic", "fsrcnn", "edsr"],
                disabled_options={
                    "edsr": "Too slow on CPU for interactive use — available in pipeline profiles",
                },
            ),
            ParamDescriptor(
                name="scale_factor",
                type="number",
                default=2,
                label="Scale Factor",
                description="Multiplicative scale factor.",
                min=2,
                max=4,
                step=1,
            ),
        ],
    ),
    "denoise": StepDescriptor(
        name="denoise",
        label="Denoise",
        description="Reduces image noise using Gaussian, median, or non-local means filtering.",
        params=[
            ParamDescriptor(
                name="method",
                type="select",
                default="gaussian",
                label="Method",
                options=["gaussian", "median", "nlmeans"],
            ),
            ParamDescriptor(
                name="strength",
                type="select",
                default="light",
                label="Strength",
                options=["light", "medium", "heavy"],
            ),
        ],
    ),
    "binarize": StepDescriptor(
        name="binarize",
        label="Binarize",
        description="Converts images to binary (black and white) using thresholding.",
        params=[
            ParamDescriptor(
                name="method",
                type="select",
                default="otsu",
                label="Method",
                options=["otsu", "adaptive_gaussian", "adaptive_mean"],
            ),
            ParamDescriptor(
                name="invert",
                type="boolean",
                default=False,
                label="Invert",
                description="Invert the binary output (white text on black background).",
            ),
            ParamDescriptor(
                name="block_size",
                type="number",
                default=11,
                label="Block Size",
                description="Neighborhood size for adaptive methods (must be odd ≥ 3).",
                min=3,
                max=99,
                step=2,
            ),
            ParamDescriptor(
                name="c",
                type="number",
                default=2,
                label="Constant C",
                description="Constant subtracted from the mean for adaptive methods.",
                min=-50,
                max=50,
                step=1,
            ),
        ],
    ),
}

STEP_ORDER = ["roi", "upscale", "grayscale", "denoise", "binarize"]


def get_all_steps() -> list[StepDescriptor]:
    """Return all step descriptors in canonical pipeline order."""
    return [STEP_REGISTRY[name] for name in STEP_ORDER]


def get_step(name: str) -> StepDescriptor | None:
    """Return a single step descriptor by name, or ``None``."""
    return STEP_REGISTRY.get(name)
