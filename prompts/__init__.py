from pathlib import Path

_DEFAULT_PROMPT_PATH = Path(__file__).parent / "llm" / "extract_title_v1.md"


def load_default_system_prompt() -> str:
    try:
        return _DEFAULT_PROMPT_PATH.read_text().strip()
    except FileNotFoundError:
        return ""


DEFAULT_SYSTEM_PROMPT = load_default_system_prompt()
