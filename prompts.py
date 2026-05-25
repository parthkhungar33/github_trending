SYSTEM_PROMPT = """\
You are a developer trends analyst writing a weekly brief about the hottest GitHub repositories.

Your audience: developers who want to stay current with what's exciting in open source \
without spending hours browsing GitHub. After reading your brief, they should be able to answer:
  1. What does this project do? (the concrete function)
  2. What problem does it solve, and why does that problem matter?
  3. What's technically interesting or novel about the approach?
  4. Should I pay attention to this? Who is it for?

Rules:
- Be specific. "A fast web framework" is weak. "A Rust HTTP server that uses io_uring for \
  zero-copy I/O, targeting services that need sub-millisecond p99 latency" is strong.
- If the README mentions a benchmark, a specific performance number, or a novel technical claim, \
  include it — readers care about evidence.
- Keep each repo card under 120 words of explanation text.
- Write in plain English. If you use a technical term, briefly explain it.
- Never construct or guess URLs — only use URLs from the input.
- End with a "## 📊 This Week's Theme" section: 2–3 sentences identifying the broader trend \
  or technology shift visible across this week's repos (if any pattern exists).\
"""


_USER_TEMPLATE = """\
Here are this week's top {count} trending GitHub repositories (week of {brief_date}).
For each repo I have provided the name, stats, description, and the first ~2500 chars of the README.

{repos_block}

---

Produce the GitHub Trending Brief in EXACTLY this format (preserve the ### headers and labels):

## 🚀 GitHub Trending — {brief_date}

[One sentence teaser: what kind of week it was for open source]

### #1. {repo_1_name} ⭐ {repo_1_stars} · {repo_1_lang}
{repo_1_url}

**What it does:** [2–3 sentences]
**Why it's interesting:** [1–2 sentences]
**Who it's for:** [1 sentence — be specific about role/use case]

... (repeat ### #N. pattern for all {count} repos) ...

## 📊 This Week's Theme
[2–3 sentences on the broader pattern or tech shift across this week's repos]
"""


def _format_repo_block(repo: dict) -> str:
    topics = ", ".join(repo["topics"]) if repo["topics"] else "none"
    readme_section = repo["readme"].strip() if repo["readme"] else "[No README available]"
    return (
        f"--- REPO #{repo['rank']} ---\n"
        f"Name: {repo['full_name']}\n"
        f"URL: {repo['url']}\n"
        f"Stars: {repo['stars']:,}\n"
        f"Language: {repo['language']}\n"
        f"Topics: {topics}\n"
        f"Created: {repo['created_at']}\n"
        f"Description: {repo['description']}\n"
        f"README:\n{readme_section}\n"
    )


def build_user_prompt(repos: list[dict], brief_date: str) -> str:
    repos_block = "\n".join(_format_repo_block(r) for r in repos)

    # Build the per-repo header placeholders for the format section
    repo_headers = ""
    for r in repos:
        stars_str = f"{r['stars']:,}"
        repo_headers += (
            f"### #{r['rank']}. {r['full_name']} ⭐ {stars_str} · {r['language']}\n"
            f"{r['url']}\n\n"
            f"**What it does:** ...\n"
            f"**Why it's interesting:** ...\n"
            f"**Who it's for:** ...\n\n"
        )

    return (
        f"Here are this week's top {len(repos)} trending GitHub repositories (week of {brief_date}).\n"
        f"For each repo I have provided the name, stats, description, and the first ~2500 chars of the README.\n\n"
        f"{repos_block}\n"
        f"---\n\n"
        f"Produce the GitHub Trending Brief in EXACTLY this format (preserve the ### headers and labels):\n\n"
        f"## 🚀 GitHub Trending — {brief_date}\n\n"
        f"[One sentence teaser: what kind of week it was for open source]\n\n"
        f"{repo_headers}"
        f"## 📊 This Week's Theme\n"
        f"[2–3 sentences on the broader pattern or tech shift across this week's repos]\n"
    )
