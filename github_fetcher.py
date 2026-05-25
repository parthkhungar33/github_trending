import base64
import logging
import time
from datetime import datetime, timezone, timedelta

import requests

from config import GITHUB_TOKEN

logger = logging.getLogger(__name__)

_API_BASE = "https://api.github.com"
_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
if GITHUB_TOKEN:
    _HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def _get(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, headers=_HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _readme(owner: str, repo: str) -> str:
    try:
        data = _get(f"{_API_BASE}/repos/{owner}/{repo}/readme")
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        # Truncate to first 2500 chars — enough context without blowing the LLM prompt
        return content[:2500]
    except Exception as e:
        logger.warning(f"readme.skip {owner}/{repo}: {e}")
        return ""


def _search_repos(created_after: str, min_stars: int, limit: int) -> list[dict]:
    params = {
        "q": f"created:>{created_after} stars:>{min_stars}",
        "sort": "stars",
        "order": "desc",
        "per_page": limit,
    }
    data = _get(f"{_API_BASE}/search/repositories", params=params)
    return data.get("items", [])


def fetch_trending(top_n: int = 10) -> list[dict]:
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    seen: set[str] = set()
    candidates: list[dict] = []

    # Primary: repos created in last 7 days with at least 50 stars
    try:
        hits = _search_repos(week_ago, min_stars=50, limit=15)
        for h in hits:
            if h["full_name"] not in seen:
                seen.add(h["full_name"])
                candidates.append(h)
        logger.info(f"fetch.week_query found={len(hits)}")
    except Exception as e:
        logger.error(f"fetch.week_query failed: {e}")

    # Fallback / supplement: broader 30-day window with higher bar (500+ stars)
    # Fills gaps when the 7-day window has fewer than top_n results
    if len(candidates) < top_n:
        try:
            time.sleep(1)
            hits = _search_repos(month_ago, min_stars=500, limit=15)
            for h in hits:
                if h["full_name"] not in seen:
                    seen.add(h["full_name"])
                    candidates.append(h)
            logger.info(f"fetch.month_query found={len(hits)}")
        except Exception as e:
            logger.error(f"fetch.month_query failed: {e}")

    # Sort by stars and take top_n
    candidates.sort(key=lambda r: r["stargazers_count"], reverse=True)
    top = candidates[:top_n]

    results = []
    for i, repo in enumerate(top):
        if i > 0:
            time.sleep(0.5)

        owner = repo["owner"]["login"]
        name = repo["name"]
        logger.info(f"fetch.repo #{i+1}: {owner}/{name} ({repo['stargazers_count']:,} ⭐)")

        results.append({
            "rank":        i + 1,
            "full_name":   repo["full_name"],
            "url":         repo["html_url"],
            "stars":       repo["stargazers_count"],
            "language":    repo.get("language") or "Unknown",
            "topics":      repo.get("topics", []),
            "description": repo.get("description") or "",
            "created_at":  repo["created_at"][:10],
            "readme":      _readme(owner, name),
        })

    return results
