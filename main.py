import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import resend
from openai import OpenAI

import email_sender
import github_fetcher
import history
from config import (
    FROM_EMAIL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    READER_CONTEXT,
    REPEAT_COOLDOWN_WEEKS,
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
    user_prompt = build_user_prompt(repos, brief_date, READER_CONTEXT)

    for attempt in range(1, 3):
        try:
            logger.info(f"llm.start attempt={attempt} model={OPENROUTER_MODEL}")
            response = _llm.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=8000,
            )
            choice = response.choices[0]
            brief = choice.message.content or ""
            if choice.finish_reason == "length":
                raise RuntimeError("LLM output hit max_tokens — brief would be truncated")
            if "### #1." not in brief:
                raise RuntimeError("LLM output is missing the expected repo cards")
            logger.info(f"llm.done usage={response.usage}")
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


def run_pipeline(dry_run: bool = False, force: bool = False) -> None:
    brief_date = _ist_today()
    logger.info(f"pipeline.start date={brief_date} dry_run={dry_run}")

    # Guard against duplicate sends (e.g. a manual trigger plus the cron on the same day).
    if not dry_run and not force and history.already_sent(brief_date):
        logger.info(f"pipeline.skip brief for {brief_date} already sent (use --force to resend)")
        return

    exclude = history.recent_repos(brief_date, REPEAT_COOLDOWN_WEEKS)
    logger.info(f"github.fetch.start excluding={len(exclude)} recently featured repos")
    repos = github_fetcher.fetch_trending(top_n=10, exclude=exclude)
    logger.info(f"github.fetch.done count={len(repos)}")

    if not repos:
        msg = "GitHub fetch returned 0 repos — aborting."
        logger.error(msg)
        if not dry_run:
            _send_failure_notification(msg)
        sys.exit(1)

    try:
        brief_md = _synthesise_brief(repos, brief_date)
    except Exception as e:
        if not dry_run:
            _send_failure_notification(str(e))
        logger.error("pipeline.aborted llm_failure")
        sys.exit(1)

    if dry_run:
        out = Path(os.getenv("DRY_RUN_OUT", "preview.html"))
        out.write_text(email_sender.build_html(brief_md, brief_date, repos))
        logger.info(f"pipeline.dry_run wrote {out.resolve()} (no email sent)")
        return

    try:
        email_sender.send_brief(brief_md, brief_date, repos)
    except Exception as e:
        logger.error(f"email.fail error={e}")
        _send_failure_notification(f"Brief was generated but the email failed to send: {e}")
        sys.exit(1)

    history.record(brief_date, [r["full_name"] for r in repos])
    logger.info(f"pipeline.complete date={brief_date}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Trending Pulse")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate the brief and write preview.html instead of emailing it")
    parser.add_argument("--force", action="store_true",
                        help="Send even if today's brief was already sent")
    args = parser.parse_args()
    run_pipeline(dry_run=args.dry_run, force=args.force or os.getenv("FORCE_SEND") == "true")
