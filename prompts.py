SYSTEM_PROMPT = """\
You are a technology-trends analyst writing a weekly brief about the fastest-rising GitHub \
repositories for a product manager.

The reader is not reading code. After your brief, they should be able to answer for each repo:
  1. What does this actually do, in plain language?
  2. Why is it gaining traction right now — what problem does it solve, and what's new about it?
  3. Who uses it?
  4. So what — what should a product team do with this signal (watch it, try it, expect \
competitors or customers to adopt it, or ignore it)?

Rules:
- Be specific. "A fast web framework" is weak. "A Rust web server that handles 3x the requests \
of Node on the same hardware, aimed at teams whose cloud bill is dominated by API traffic" is strong.
- If the README states a benchmark, a number, or a notable adopter, include it — evidence beats adjectives.
- Use the "+N this week" star gain to judge momentum. A big total with a small weekly gain is a \
fixture, not a trend; say so briefly if relevant.
- Keep each repo card under 110 words. No filler, no hype words ("revolutionary", "game-changer").
- Write in plain English. If you must use a technical term, explain it in a few words.
- Never construct or guess URLs — only use URLs from the input.
- The "PM takeaway" must be one concrete, actionable sentence — not a restatement of what it does.\
"""


def _format_repo_block(repo: dict) -> str:
    topics = ", ".join(repo["topics"]) if repo["topics"] else "none"
    readme_section = repo["readme"].strip() if repo["readme"] else "[No README available]"
    week_stars = repo.get("stars_this_week", 0)
    return (
        f"--- REPO #{repo['rank']} ---\n"
        f"Name: {repo['full_name']}\n"
        f"URL: {repo['url']}\n"
        f"Stars: {repo['stars']:,} total (+{week_stars:,} this week)\n"
        f"Language: {repo['language']}\n"
        f"Topics: {topics}\n"
        f"Created: {repo['created_at']}\n"
        f"Description: {repo['description']}\n"
        f"README (cleaned excerpt):\n{readme_section}\n"
    )


def build_user_prompt(repos: list[dict], brief_date: str, reader_context: str = "") -> str:
    repos_block = "\n".join(_format_repo_block(r) for r in repos)

    repo_headers = ""
    for r in repos:
        repo_headers += (
            f"### #{r['rank']}. {r['full_name']} ⭐ {r['stars']:,} · {r['language']}\n"
            f"{r['url']}\n\n"
            f"**What it does:** ...\n"
            f"**Why it's rising:** ...\n"
            f"**Who it's for:** ...\n"
            f"**PM takeaway:** ...\n\n"
        )

    context_block = ""
    if reader_context.strip():
        context_block = (
            f"About the reader: {reader_context.strip()}\n"
            f"Where a repo is genuinely relevant to this, tie the PM takeaway to it. "
            f"Don't force a connection that isn't there.\n\n"
        )

    return (
        f"Here are this week's top {len(repos)} rising GitHub repositories (week of {brief_date}), "
        f"ranked by stars gained this week. Each has stats, description, and a cleaned README excerpt.\n\n"
        f"{context_block}"
        f"{repos_block}\n"
        f"---\n\n"
        f"Produce the brief in EXACTLY this format. Keep the ### headers and the bold labels "
        f"exactly as shown, one label per line:\n\n"
        f"## 🚀 GitHub Trending — {brief_date}\n\n"
        f"[One sentence: what kind of week it was in open source]\n\n"
        f"{repo_headers}"
        f"## 📊 This Week's Theme\n"
        f"[2–3 sentences on the broader pattern across this week's repos, and what it means "
        f"for product teams]\n"
    )
