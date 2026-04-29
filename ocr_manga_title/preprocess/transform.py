"""Coordinate transform utilities for mapping bbox coordinates between image spaces.

When preprocessing steps like upscale or ROI crop are applied, the OCR engine
operates on the transformed image.  Bounding box coordinates returned by OCR
are in the *preprocessed* coordinate space and must be inverse-mapped back to
the *original* image space for correct overlay rendering.

Forward mapping (original → preprocessed)::

    pp = scale * orig + offset

Inverse mapping (preprocessed → original)::

    orig = (pp - offset) / scale

Multiple steps are composed by chaining their forward transforms.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CoordinateTransform:
    """Affine-like 2D coordinate transform (per-axis scale + offset).

    Default-constructed as the identity transform.
    """

    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0

    def inverse_map_point(self, x: float, y: float) -> tuple[float, float]:
        return (
            (x - self.offset_x) / self.scale_x,
            (y - self.offset_y) / self.scale_y,
        )

    def inverse_map_bbox(self, bbox: list[list[float]]) -> list[list[float]]:
        return [list(self.inverse_map_point(p[0], p[1])) for p in bbox]

    def compose(self, other: CoordinateTransform) -> CoordinateTransform:
        """Compose two transforms: *self* is applied first, then *other*.

        Combined forward mapping::

            B(A(x)) = B.scale * (A.scale * x + A.offset) + B.offset
                    = (B.scale * A.scale) * x + (B.scale * A.offset + B.offset)
        """
        return CoordinateTransform(
            scale_x=other.scale_x * self.scale_x,
            scale_y=other.scale_y * self.scale_y,
            offset_x=other.scale_x * self.offset_x + other.offset_x,
            offset_y=other.scale_y * self.offset_y + other.offset_y,
        )

    @staticmethod
    def identity() -> CoordinateTransform:
        return CoordinateTransform()

    @staticmethod
    def from_step(step_name: str, metadata: dict) -> CoordinateTransform:
        """Build a transform from a single preprocessing step's metadata.

        Recognised steps:

        * **upscale** — scale by ``scale_factor``.
        * **roi** — offset by the crop origin ``(x, y)`` from ``bounding_box``.
        * All other steps return the identity transform.
        """
        if step_name == "upscale":
            sf = metadata.get("scale_factor", 1)
            if metadata.get("skipped", False) or sf < 2:
                return CoordinateTransform.identity()
            return CoordinateTransform(
                scale_x=float(sf),
                scale_y=float(sf),
            )

        if step_name == "roi":
            if not metadata.get("crop_performed", False):
                return CoordinateTransform.identity()
            bb = metadata.get("bounding_box", {})
            return CoordinateTransform(
                offset_x=-float(bb.get("x", 0)),
                offset_y=-float(bb.get("y", 0)),
            )

        return CoordinateTransform.identity()

    @staticmethod
    def from_pipeline(steps: list[tuple[str, dict]]) -> CoordinateTransform:
        """Compose transforms from an ordered list of ``(step_name, metadata)`` pairs.

        Steps are applied in pipeline order (first step first).  The resulting
        transform maps *original* coordinates to *preprocessed* coordinates.
        Use :meth:`inverse_map_bbox` to map OCR bboxes back to original space.
        """
        result = CoordinateTransform.identity()
        for step_name, metadata in steps:
            step_t = CoordinateTransform.from_step(step_name, metadata)
            result = result.compose(step_t)
        return result
