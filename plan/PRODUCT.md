# Manga OCR — Product Description

## What Is It

Manga OCR is a self-hosted tool that extracts manga title references and codes from social media post images. It turns unstructured screenshots and photos from platforms like X/Twitter and Facebook into a structured, searchable manga catalog.

## Why It Exists

Manga distributors, retailers, and enthusiasts frequently post images containing manga titles, ISBN codes, and product identifiers on social media. These are embedded in photos of book covers, storefront screenshots, promotional art, and manga panels. Manually transcribing Japanese and English text from these images is tedious and error-prone. Manga OCR automates this extraction.

## Who It Is For

A single operator (the project owner) who wants to maintain a personal manga catalog by collecting references from social media. This is a hobby project processing fewer than 50 posts per day on a single VPS.

## How It Works

1. **Input**: The operator submits a social media post image — either by uploading a file or pasting a URL from X/Twitter or Facebook.
2. **OCR**: The image is processed by multiple OCR models in parallel (manga-ocr for Japanese manga text, Tesseract for general text, with additional models available).
3. **Post-Processing**: Raw OCR output is cleaned and structured by an LLM (via OpenRouter) that extracts the manga title (English + Japanese), codes, and identifiers. Rule-based matching handles ISBN formats and known patterns.
4. **Catalog**: The extracted, structured data is stored in a searchable manga catalog with confidence scores. Low-confidence results are flagged for manual review.

## Key Capabilities

- **Multi-model OCR**: Runs several OCR engines in parallel and compares results for higher accuracy
- **Bilingual support**: Handles both English and Japanese text in images
- **LLM-powered extraction**: Uses OpenRouter LLMs to clean raw OCR text and extract structured manga metadata
- **Prompt versioning**: OCR and LLM prompts are versioned via Agenta.ai, with local copies for offline use
- **Results comparison**: Side-by-side comparison of outputs across different model and prompt configurations
- **Configurable pipeline**: Models can be enabled/disabled; parameters and LLM model selection are configured via files

## Technology

| Component | Stack |
|-----------|-------|
| Frontend | React + TypeScript |
| Backend | FastAPI (Python 3.12) |
| Database | PostgreSQL |
| Task Queue | Dramatiq + Redis |
| OCR Models | manga-ocr, Tesseract, PaddleOCR, EasyOCR, GLM OCR |
| LLM | OpenRouter (multi-model) |
| Prompt Management | Agenta.ai |
| Deployment | Docker Compose on single VPS |
