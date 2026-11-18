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

# "Proven" floor: trending repos below this many total stars are dropped, so the
# brief favours established projects gaining momentum over brand-new viral repos.
PROVEN_MIN_STARS   = int(_optional("PROVEN_MIN_STARS", "1000"))
OPENROUTER_MODEL   = _require("OPENROUTER_MODEL")
RESEND_API_KEY     = _require("RESEND_API_KEY")
FROM_EMAIL         = _require("FROM_EMAIL")
TO_EMAIL           = _require("TO_EMAIL")

# Skip repos that were featured in any brief within this many weeks (0 = never skip).
REPEAT_COOLDOWN_WEEKS = int(_optional("REPEAT_COOLDOWN_WEEKS", "4"))

# Optional one-or-two-sentence description of the reader's company/product, so the
# LLM can tie "PM takeaway" lines to it. Keep it in a secret, not in this public repo.
READER_CONTEXT     = _optional("READER_CONTEXT")
