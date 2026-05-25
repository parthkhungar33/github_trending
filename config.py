import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


GITHUB_TOKEN       = _optional("GITHUB_TOKEN")   # Optional — raises rate limit from 60 to 5000 req/hr
OPENROUTER_API_KEY = _require("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = _require("OPENROUTER_MODEL")
RESEND_API_KEY     = _require("RESEND_API_KEY")
FROM_EMAIL         = _require("FROM_EMAIL")
TO_EMAIL           = _require("TO_EMAIL")
