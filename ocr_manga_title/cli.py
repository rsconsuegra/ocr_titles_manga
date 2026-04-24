"""CLI entry point for running the OCR pipeline on a single image."""

import json
import sys

from ocr_manga_title.config import load_config, load_ocr_config, load_preprocess_config
from ocr_manga_title.engine import OCREngine


def main():
    """CLI entry point for running the OCR pipeline on a single image."""
    if len(sys.argv) < 2:
        print("Usage: python -m ocr_manga_title.cli <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    config = load_config()
    ocr_config = load_ocr_config()
    preprocess_config = load_preprocess_config()

    engine = OCREngine(config, ocr_config, preprocess_config)

    try:
        result = engine.process(image_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
