"""Record of past briefs, stored as history.json in the repo.

The GitHub Actions workflow commits this file back after every successful send.
That gives the pipeline memory between runs (skip repos featured recently, never
send the same date twice) and, as a side effect, keeps the repo "active" so
GitHub doesn't auto-disable the scheduled workflow after 60 days without commits.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

HISTORY_PATH = Path(__file__).parent / "history.json"
_KEEP_WEEKS = 26  # prune older entries so the file stays small


def _load() -> dict:
    try:
        return json.loads(HISTORY_PATH.read_text())
    except FileNotFoundError:
        return {"briefs": {}}
    except Exception as e:
        logger.warning(f"history.load failed, starting fresh: {e}")
        return {"briefs": {}}


def already_sent(brief_date: str) -> bool:
    return brief_date in _load()["briefs"]


def recent_repos(brief_date: str, weeks: int) -> set[str]:
    """Repo names featured in briefs within `weeks` weeks before brief_date."""
    if weeks <= 0:
        return set()
    cutoff = date.fromisoformat(brief_date) - timedelta(weeks=weeks)
    names: set[str] = set()
    for d, repos in _load()["briefs"].items():
        if cutoff <= date.fromisoformat(d) < date.fromisoformat(brief_date):
            names.update(repos)
    return names


def record(brief_date: str, repo_names: list[str]) -> None:
    data = _load()
    data["briefs"][brief_date] = repo_names
    cutoff = date.fromisoformat(brief_date) - timedelta(weeks=_KEEP_WEEKS)
    data["briefs"] = {
        d: r for d, r in sorted(data["briefs"].items())
        if date.fromisoformat(d) >= cutoff
    }
    HISTORY_PATH.write_text(json.dumps(data, indent=2) + "\n")
    logger.info(f"history.recorded date={brief_date} repos={len(repo_names)}")
