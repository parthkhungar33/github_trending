# 🚀 GitHub Trending Pulse

An automated weekly newsletter pipeline that discovers the hottest trending GitHub repositories, uses an LLM to explain what each one actually does and why it matters, and emails you a polished HTML digest — hands-free, every week.

No more scrolling through `github.com/trending` and guessing what a repo is from a one-line tagline. Every Tuesday morning, a clear, skimmable brief lands in your inbox.

---

## Why I built this (a product manager's problem)

As a product manager, my job depends on knowing where the technology is heading *before* it shows up in a competitor's release notes or a customer's feature request. But staying current with open source is genuinely hard:

- **The signal is buried in noise.** `github.com/trending` is a wall of repo names and star counts. Most of them are toy projects, one-week hype, or renamed forks. Figuring out which ones actually matter means opening a dozen tabs and reading READMEs I don't have time for.
- **Raw stars lie.** A repo with 40k stars that's been around for five years isn't a *trend* — it's a fixture. What I care about is *momentum*: what is gaining traction right now, and is it credible enough to bet attention on?
- **I don't need code — I need meaning.** I don't want a diff. I want to know: what does this do, what problem does it solve, and *should my team care?*

This pipeline turns that hour-long weekly chore into a two-minute read.

### How it helps me as a PM

- **Competitive & market radar.** Surfaces the tools, frameworks, and infrastructure developers are adopting *this week* — often the earliest visible signal of a shift my roadmap should account for.
- **Answers the PM questions, not the engineer questions.** Every repo is framed as **What it does · Why it's rising · Who it's for · PM takeaway** — the language of positioning, use cases, and target users, not implementation.
- **Spots the theme, not just the items.** The closing "This Week's Theme" section names the *pattern* across the week's repos (e.g. "AI agent frameworks are consolidating"), which is exactly the altitude a PM needs for strategy conversations.
- **Zero maintenance.** It runs itself on a schedule and lands in my inbox. Staying informed becomes a default, not a task I have to remember.

### How it uniquely captures the *right* signal

Most "trending" tools just re-list GitHub's page. This pipeline filters for signal deliberately:

- **Momentum over vanity.** It reads the *weekly* trending window — repos ranked by **stars gained this week**, not lifetime totals — so it catches what's accelerating, not what's already famous.
- **A "proven" credibility floor.** It drops anything below a configurable star threshold (`PROVEN_MIN_STARS`, default 1,000), filtering out weekend experiments and hype spikes so I only see projects with real adoption behind the momentum. **Established projects catching fire** — the sweet spot — rise to the top.
- **Meaning, not metadata.** Instead of dumping stats, it feeds each repo's actual README to an LLM that explains it in plain product language and connects it to a broader trend — turning data into a decision-ready brief.

The result: a signal that's *early* (momentum-based), *credible* (star-floored), and *legible* (explained for a non-engineer decision-maker).

---

## What it does

Every week the pipeline runs end-to-end:

1. **Fetch** — Scrapes [github.com/trending](https://github.com/trending) for the weekly window, so repos are ranked by *momentum* (stars gained this week), not just all-time star count. Each candidate is enriched with metadata and its README via the GitHub API.
2. **Filter** — Drops repos below a configurable "proven" star floor (`PROVEN_MIN_STARS`, default 1,000), favouring established projects catching fire over brand-new viral flashes. If the scrape ever fails, it falls back to the GitHub Search API so the unattended run still produces a brief.
3. **Synthesise** — Sends each repo's stats + README to an LLM (via [OpenRouter](https://openrouter.ai)) that writes a structured card for each: **What it does · Why it's rising · Who it's for · PM takeaway**, plus a closing "This Week's Theme" section identifying the broader trend.
4. **Send** — Renders the brief into a clean, responsive HTML email (GitHub-style dark header, per-repo cards, language badges) and delivers it via [Resend](https://resend.com). If any critical step fails, it emails a failure notification instead of dying silently.

The whole thing runs unattended on a **GitHub Actions cron schedule** — no server required.

---

## Sample output

Each repo becomes a card like:

> ### #1. anthropics/claude-engineer ⭐ 9,412 · Python
> **What it does:** An open-source CLI that wraps Claude's API into an autonomous coding agent...
> **Why it's rising:** Unlike autocomplete tools, this operates at the task level...
> **Who it's for:** Backend engineers who want to automate boilerplate-heavy tasks...
> **PM takeaway:** Expect customers to ask for task-level automation, not just suggestions...

Followed by a **📊 This Week's Theme** summary tying the week's repos together.

---

## Architecture

| File | Responsibility |
|------|----------------|
| [main.py](main.py) | Pipeline orchestration — fetch → synthesise → send, with retries, failure alerts, `--dry-run` and duplicate-send guard |
| [history.py](history.py) | Reads/writes `history.json` — recently featured repos and dates already sent |
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
| `OPENROUTER_MODEL` | ✅ | Model slug, e.g. `anthropic/claude-sonnet-5.5` |
| `RESEND_API_KEY` | ✅ | API key for [Resend](https://resend.com) |
| `FROM_EMAIL` | ✅ | Verified sender address |
| `TO_EMAIL` | ✅ | Recipient address |
| `GITHUB_TOKEN` | ⬜ | Optional — raises the GitHub API rate limit from 60 to 5,000 req/hr |
| `PROVEN_MIN_STARS` | ⬜ | Minimum all-time stars to include a repo (default `1000`) |
| `REPEAT_COOLDOWN_WEEKS` | ⬜ | Skip repos featured in any brief within this many weeks (default `4`, `0` disables) |
| `READER_CONTEXT` | ⬜ | One or two sentences about your company/product, so the "PM takeaway" lines can tie trends to it. Keep it in a secret — this repo is public |

### 3. Run it

```bash
python main.py --dry-run   # generate the brief and write preview.html — no email sent
python main.py             # generate and email it
python main.py --force     # resend even if today's brief was already sent
```

---

## Automated scheduling

The included GitHub Actions workflow runs the pipeline **every Tuesday at 9:00 AM IST** and can also be triggered manually from the Actions tab (tick **force** to resend a brief already sent that day).

After each successful send, the workflow commits `history.json`, a record of which repos each brief featured. This lets the next run skip recently featured repos, prevents duplicate sends on the same day, and keeps the repo active, so GitHub never auto-disables the schedule after 60 days without commits. Add the environment variables above as **repository secrets** (`Settings → Secrets and variables → Actions`) and the newsletter runs itself — no infrastructure to maintain.

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
