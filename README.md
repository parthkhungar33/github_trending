# 🚀 GitHub Trending Pulse

An automated weekly newsletter pipeline that discovers the hottest trending GitHub repositories, uses an LLM to explain what each one actually does and why it matters, and emails you a polished HTML digest — hands-free, every week.

No more scrolling through `github.com/trending` and guessing what a repo is from a one-line tagline. Every Tuesday morning, a clear, skimmable brief lands in your inbox.

---

## What it does

Every week the pipeline runs end-to-end:

1. **Fetch** — Scrapes [github.com/trending](https://github.com/trending) for the weekly window, so repos are ranked by *momentum* (stars gained this week), not just all-time star count. Each candidate is enriched with metadata and its README via the GitHub API.
2. **Filter** — Drops repos below a configurable "proven" star floor (`PROVEN_MIN_STARS`, default 1,000), favouring established projects catching fire over brand-new viral flashes. If the scrape ever fails, it falls back to the GitHub Search API so the unattended run still produces a brief.
3. **Synthesise** — Sends each repo's stats + README to an LLM (via [OpenRouter](https://openrouter.ai)) that writes a structured card for each: **What it does · Why it's interesting · Who it's for**, plus a closing "This Week's Theme" section identifying the broader trend.
4. **Send** — Renders the brief into a clean, responsive HTML email (GitHub-style dark header, per-repo cards, language badges) and delivers it via [Resend](https://resend.com). If any critical step fails, it emails a failure notification instead of dying silently.

The whole thing runs unattended on a **GitHub Actions cron schedule** — no server required.

---

## Sample output

Each repo becomes a card like:

> ### #1. anthropics/claude-engineer ⭐ 9,412 · Python
> **What it does:** An open-source CLI that wraps Claude's API into an autonomous coding agent...
> **Why it's interesting:** Unlike autocomplete tools, this operates at the task level...
> **Who it's for:** Backend engineers who want to automate boilerplate-heavy tasks...

Followed by a **📊 This Week's Theme** summary tying the week's repos together.

---

## Architecture

| File | Responsibility |
|------|----------------|
| [main.py](main.py) | Pipeline orchestration — fetch → synthesise → send, with retries and failure alerts |
| [github_fetcher.py](github_fetcher.py) | Scrapes trending, enriches via GitHub API, applies the "proven" filter, API fallback |
| [prompts.py](prompts.py) | System + user prompts and the strict output format for the LLM |
| [email_sender.py](email_sender.py) | Markdown → responsive HTML email rendering and Resend delivery |
| [config.py](config.py) | Environment-variable configuration loading |
| [.github/workflows/weekly-trending.yml](.github/workflows/weekly-trending.yml) | Weekly cron schedule (Tuesdays 9:00 AM IST) + manual trigger |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file (or set repository secrets for GitHub Actions):

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | ✅ | API key for [OpenRouter](https://openrouter.ai) |
| `OPENROUTER_MODEL` | ✅ | Model slug, e.g. `anthropic/claude-sonnet-4` |
| `RESEND_API_KEY` | ✅ | API key for [Resend](https://resend.com) |
| `FROM_EMAIL` | ✅ | Verified sender address |
| `TO_EMAIL` | ✅ | Recipient address |
| `GITHUB_TOKEN` | ⬜ | Optional — raises the GitHub API rate limit from 60 to 5,000 req/hr |
| `PROVEN_MIN_STARS` | ⬜ | Minimum all-time stars to include a repo (default `1000`) |

### 3. Run it

```bash
python main.py
```

---

## Automated scheduling

The included GitHub Actions workflow runs the pipeline **every Tuesday at 9:00 AM IST** and can also be triggered manually from the Actions tab. Add the environment variables above as **repository secrets** (`Settings → Secrets and variables → Actions`) and the newsletter runs itself — no infrastructure to maintain.

---

## Tech stack

- **Python 3.11**
- **BeautifulSoup** — trending page scraping
- **GitHub REST API** — repo metadata + README enrichment
- **OpenRouter** (OpenAI-compatible SDK) — LLM synthesis
- **Resend** — transactional email delivery
- **GitHub Actions** — scheduled, serverless execution

---

## License

MIT
