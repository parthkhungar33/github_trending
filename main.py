import logging
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import resend
from openai import OpenAI

import email_sender
import github_fetcher
from config import (
    FROM_EMAIL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    RESEND_API_KEY,
    TO_EMAIL,
)
from prompts import SYSTEM_PROMPT, build_user_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

_llm = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


def _synthesise_brief(repos: list[dict], brief_date: str) -> str:
    user_prompt = build_user_prompt(repos, brief_date)

    for attempt in range(1, 3):
        try:
            logger.info(f"llm.start attempt={attempt}")
            response = _llm.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=4000,
            )
            brief = response.choices[0].message.content
            logger.info("llm.done")
            return brief
        except Exception as e:
            logger.error(f"llm.fail attempt={attempt} error={e}")
            if attempt < 2:
                logger.info("llm.retry waiting 30s")
                time.sleep(30)
            else:
                raise


def _send_failure_notification(error: str) -> None:
    try:
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [TO_EMAIL],
            "subject": "⚠️ GitHub Trending Pulse — Pipeline Failed",
            "html":    f"<p>The weekly GitHub trending pipeline failed.</p><pre>{error}</pre>",
        })
    except Exception as e:
        logger.error(f"failure_notification.fail error={e}")


def _ist_today() -> str:
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")


def run_pipeline() -> None:
    brief_date = _ist_today()
    logger.info(f"pipeline.start date={brief_date}")

    logger.info("github.fetch.start")
    repos = github_fetcher.fetch_trending(top_n=10)
    logger.info(f"github.fetch.done count={len(repos)}")

    if not repos:
        msg = "GitHub fetch returned 0 repos — aborting."
        logger.error(msg)
        _send_failure_notification(msg)
        sys.exit(1)

    try:
        brief_md = _synthesise_brief(repos, brief_date)
    except Exception as e:
        _send_failure_notification(str(e))
        logger.error("pipeline.aborted llm_failure")
        sys.exit(1)

    try:
        email_sender.send_brief(brief_md, brief_date)
    except Exception as e:
        logger.error(f"email.fail error={e}")

    logger.info(f"pipeline.complete date={brief_date}")


if __name__ == "__main__":
    run_pipeline()
