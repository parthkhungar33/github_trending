from __future__ import annotations

import base64
import logging
import re
import time
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup

from config import GITHUB_TOKEN, PROVEN_MIN_STARS

logger = logging.getLogger(__name__)

_API_BASE = "https://api.github.com"
_TRENDING_URL = "https://github.com/trending"
_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
if GITHUB_TOKEN:
    _HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

# github.com/trending is an HTML page, not an API — it expects a browser-ish client.
_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; github-trending-pulse/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def _get(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, headers=_HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


README_CHARS = 4000


def _clean_readme(text: str) -> str:
    """Strip the parts of a README that carry no meaning for the LLM.

    READMEs often open with HTML wrappers, logos, badge rows and image links; left
    in, they eat most of the excerpt before any real description appears.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)                 # HTML comments
    text = re.sub(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)", "", text)       # linked badges
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)                    # images
    text = re.sub(r"<img[^>]*>", "", text, flags=re.I)
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)                       # remaining HTML tags
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)                # links -> link text
    text = re.sub(r"^\s*\|?[\s|:-]+\|?\s*$", "", text, flags=re.M)        # table separators
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _readme(owner: str, repo: str) -> str:
    try:
        data = _get(f"{_API_BASE}/repos/{owner}/{repo}/readme")
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return _clean_readme(content)[:README_CHARS]
    except Exception as e:
        logger.warning(f"readme.skip {owner}/{repo}: {e}")
        return ""


def _scrape_trending(since: str = "weekly") -> list[dict]:
    """Scrape github.com/trending for the given window ('daily' | 'weekly' | 'monthly').

    Returns repos in GitHub's trending order — i.e. ranked by stars gained in the
    window (momentum), not by all-time star count. Each entry carries the
    'stars_this_week' delta parsed from the page.
    """
    resp = requests.get(
        _TRENDING_URL, params={"since": since}, headers=_BROWSER_HEADERS, timeout=20
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    entries: list[dict] = []
    for row in soup.select("article.Box-row"):
        anchor = row.select_one("h2 a")
        if not anchor:
            continue
        full_name = anchor.get("href", "").strip("/")
        # Expect exactly "owner/repo"
        if full_name.count("/") != 1:
            continue

        # The "N stars this week/today" delta lives in the float-right span.
        period_stars = 0
        delta = row.select_one("span.d-inline-block.float-sm-right")
        if delta:
            m = re.search(r"([\d,]+)", delta.get_text())
            if m:
                period_stars = int(m.group(1).replace(",", ""))

        entries.append({"full_name": full_name, "period_stars": period_stars})

    return entries


def _search_repos(created_after: str, min_stars: int, limit: int) -> list[dict]:
    params = {
        "q": f"created:>{created_after} stars:>{min_stars}",
        "sort": "stars",
        "order": "desc",
        "per_page": limit,
    }
    data = _get(f"{_API_BASE}/search/repositories", params=params)
    return data.get("items", [])


def _build_result(rank: int, repo: dict, period_stars: int) -> dict:
    owner = repo["owner"]["login"]
    name = repo["name"]
    return {
        "rank":            rank,
        "full_name":       repo["full_name"],
        "url":             repo["html_url"],
        "stars":           repo["stargazers_count"],
        "stars_this_week": period_stars,
        "language":        repo.get("language") or "Unknown",
        "topics":          repo.get("topics", []),
        "description":     repo.get("description") or "",
        "created_at":      repo["created_at"][:10],
        "readme":          _readme(owner, name),
    }


def fetch_trending(
    top_n: int = 10, since: str = "weekly", exclude: set[str] | None = None
) -> list[dict]:
    """Top trending repos that are also 'proven'.

    Primary source is github.com/trending (weekly), which ranks by momentum —
    stars gained this week — so it surfaces established projects catching fire,
    not just brand-new repos. Each candidate is then enriched via the GitHub API
    and dropped if its all-time star count is below PROVEN_MIN_STARS.

    If the trending scrape yields nothing (e.g. GitHub changes its HTML), we fall
    back to the API search so the unattended pipeline still produces a brief.

    `exclude` holds repo names featured in recent briefs; they are skipped so each
    week's email surfaces new projects instead of the same fixtures.
    """
    exclude = {name.lower() for name in (exclude or set())}
    results: list[dict] = []

    # Primary: scrape the trending page, enrich + filter each in trending order.
    try:
        trending = _scrape_trending(since)
        logger.info(f"trending.scraped since={since} count={len(trending)}")
    except Exception as e:
        logger.error(f"trending.scrape failed: {e}")
        trending = []

    for entry in trending:
        if len(results) >= top_n:
            break
        full_name = entry["full_name"]
        if full_name.lower() in exclude:
            logger.info(f"recent_filter.skip {full_name} (featured in a recent brief)")
            continue
        try:
            repo = _get(f"{_API_BASE}/repos/{full_name}")
        except Exception as e:
            logger.warning(f"meta.skip {full_name}: {e}")
            continue

        stars = repo.get("stargazers_count", 0)
        if stars < PROVEN_MIN_STARS:
            logger.info(f"proven_filter.skip {full_name} stars={stars:,} < {PROVEN_MIN_STARS:,}")
            continue

        rank = len(results) + 1
        logger.info(
            f"fetch.repo #{rank}: {full_name} "
            f"({stars:,} ⭐, +{entry['period_stars']:,} this week)"
        )
        results.append(_build_result(rank, repo, entry["period_stars"]))
        time.sleep(0.5)

    if results:
        return results

    # Fallback: API search for proven repos created in the last 30 days.
    logger.warning("trending produced 0 results — falling back to API search")
    month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        hits = _search_repos(month_ago, min_stars=PROVEN_MIN_STARS, limit=top_n * 3)
    except Exception as e:
        logger.error(f"fallback.search failed: {e}")
        return []

    hits = [h for h in hits if h["full_name"].lower() not in exclude]
    for i, repo in enumerate(hits[:top_n]):
        if i > 0:
            time.sleep(0.5)
        logger.info(f"fallback.repo #{i+1}: {repo['full_name']} ({repo['stargazers_count']:,} ⭐)")
        results.append(_build_result(i + 1, repo, 0))

    return results
