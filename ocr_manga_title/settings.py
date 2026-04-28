"""Centralized application settings — single source of truth for env vars and defaults."""

import os

# --- Database ---
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://manga_ocr:manga_ocr_dev@localhost:5432/manga_ocr",
)
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_WORKER_POOL_SIZE: int = int(os.getenv("DB_WORKER_POOL_SIZE", "2"))
DB_WORKER_MAX_OVERFLOW: int = int(os.getenv("DB_WORKER_MAX_OVERFLOW", "0"))

# --- Redis ---
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# --- OpenRouter / LLM ---
OPENROUTER_DEFAULT_MODEL: str = "google/gemini-2.5-flash"
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENROUTER_REQUEST_TIMEOUT: float = 30.0
OPENROUTER_MAX_RETRIES: int = 3
OPENROUTER_API_KEY_PREFIX: str = "sk-"
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

# --- Ollama ---
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "")
OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "ollama")
OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_DEFAULT_MODEL: str = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3")

# --- Config file paths ---
CONFIG_PATH: str = "config/configs.toml"
OCR_CONFIG_PATH: str = "config/ocrs.yaml"
PREPROCESS_CONFIG_PATH: str = "config/preprocess.yaml"

# --- Upload limits ---
UPLOAD_DIR: str = "uploads"
ALLOWED_EXTENSIONS: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".tiff",
    ".tif",
    ".bmp",
)
MAX_FILE_SIZE: int = 20 * 1024 * 1024
MAX_FILES: int = 10

# --- Images ---
IMAGES_PATH: str = os.getenv("IMAGES_PATH", "/app/uploads")

# --- Cache ---
CACHE_DIR: str = os.getenv("CACHE_DIR", "/app/cache")
CACHE_TTL_DAYS: int = int(os.getenv("CACHE_TTL_DAYS", "7"))
CACHE_SWEEPER_INTERVAL_SECONDS: int = int(
    os.getenv("CACHE_SWEEPER_INTERVAL_SECONDS", "3600")
)

# --- CORS ---
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173"
).split(",")

# --- Encryption ---
SERVER_SECRET: str = os.getenv("SERVER_SECRET", "")
