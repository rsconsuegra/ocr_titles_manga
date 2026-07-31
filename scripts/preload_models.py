"""Build-time pre-download of local OCR model weights.

Run during the Docker image build so that PaddleOCR/EasyOCR weights are baked
into the image at ``$MODEL_DATA_DIR`` instead of being downloaded on first boot.

Reuses :func:`ocr_manga_title.services.warmup.warmup_models` as the single source
of truth for which models get loaded and how.

Exits non-zero only if no model could be warmed (loud build failure); per-model
failures are logged and tolerated so an optional engine being uninstallable in
the build environment does not block the build.
"""

from __future__ import annotations

import sys

from ocr_manga_title.services.warmup import warmup_models


def main() -> int:
    warmed = warmup_models()
    if not warmed:
        print("ERROR: no local OCR models were warmed up", file=sys.stderr)
        return 1
    print(f"Preloaded model weights: {', '.join(warmed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
