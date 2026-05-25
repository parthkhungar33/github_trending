import re
import logging

import resend

from config import RESEND_API_KEY, FROM_EMAIL, TO_EMAIL

logger = logging.getLogger(__name__)
resend.api_key = RESEND_API_KEY

# GitHub's official language color palette (subset)
_LANG_COLORS = {
    "Python":           "#3572A5",
    "JavaScript":       "#f1e05a",
    "TypeScript":       "#3178c6",
    "Rust":             "#dea584",
    "Go":               "#00ADD8",
    "Java":             "#b07219",
    "C++":              "#f34b7d",
    "C":                "#555555",
    "C#":               "#178600",
    "Ruby":             "#701516",
    "Swift":            "#F05138",
    "Kotlin":           "#A97BFF",
    "Shell":            "#89e051",
    "CSS":              "#563d7c",
    "HTML":             "#e34c26",
    "Jupyter Notebook": "#DA5B0B",
    "Vue":              "#41b883",
    "Svelte":           "#ff3e00",
    "Dart":             "#00B4AB",
    "R":                "#198CE7",
    "PHP":              "#4F5D95",
    "Scala":            "#c22d40",
    "Zig":              "#ec915c",
    "Lua":              "#000080",
    "Haskell":          "#5e5086",
    "Nix":              "#7e7eff",
}


def _lang_badge(language: str) -> str:
    color = _LANG_COLORS.get(language, "#6e7681")
    text_color = "#fff" if language != "JavaScript" else "#1a1a1a"
    return (
        f'<span style="display:inline-block;background:{color};color:{text_color};'
        f'padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">'
        f'{language}</span>'
    )


def _inline_md(text: str) -> str:
    """Convert inline markdown (bold, links) to HTML."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code style="background:#f0f0f0;padding:1px 4px;border-radius:3px;font-size:12px;">\1</code>', text)
    # Markdown links
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^\)]+)\)',
        r'<a href="\2" style="color:#0969da;text-decoration:none;">\1</a>',
        text,
    )
    return text


def _body_to_html(md: str) -> str:
    """Convert repo card body markdown to HTML paragraphs."""
    result = []
    for line in md.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        processed = _inline_md(stripped)
        if processed.startswith('<'):
            result.append(processed)
        else:
            result.append(
                f'<p style="margin:0 0 8px;line-height:1.55;color:#444;font-size:13px;">'
                f'{processed}</p>'
            )
    return '\n'.join(result)


def _render_repo_card(raw: str) -> str:
    """Render a single repo section (everything after '### ') as an HTML card."""
    lines = raw.strip().split('\n')
    header = lines[0].strip()

    # Parse: #N. owner/repo ⭐ 12,345 · Python
    m = re.match(
        r'#(\d+)\.\s+([\w.\-]+/[\w.\-]+)\s+⭐\s+([\d,]+)\s+·\s+(.+)$',
        header,
    )
    rank      = m.group(1) if m else "?"
    repo_name = m.group(2).strip() if m else header.lstrip('#').strip()
    stars     = m.group(3) if m else ""
    language  = m.group(4).strip() if m else ""

    # Line 1 is the bare GitHub URL (if present)
    github_url = ""
    body_start = 1
    if len(lines) > 1 and lines[1].strip().startswith("https://github.com"):
        github_url = lines[1].strip()
        body_start = 2

    body_md = '\n'.join(lines[body_start:]).strip()
    body_html = _body_to_html(body_md)

    # Header elements
    rank_badge = (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'min-width:26px;height:26px;background:#0d1117;color:#fff;border-radius:50%;'
        f'font-size:12px;font-weight:700;padding:0 2px;">{rank}</span>'
    )

    if github_url:
        name_html = (
            f'<a href="{github_url}" style="color:#0d1117;text-decoration:none;'
            f'font-weight:700;font-size:15px;">{repo_name}</a>'
        )
    else:
        name_html = f'<span style="font-weight:700;font-size:15px;">{repo_name}</span>'

    meta_parts = []
    if stars:
        meta_parts.append(
            f'<span style="color:#9a6700;font-weight:600;font-size:12px;">⭐ {stars} stars</span>'
        )
    if language and language != "Unknown":
        meta_parts.append(_lang_badge(language))

    meta_html = (
        f'<div style="margin-top:4px;">'
        + '&nbsp;&nbsp;'.join(meta_parts)
        + '</div>'
        if meta_parts else ''
    )

    button_html = (
        f'<a href="{github_url}" style="display:inline-block;background:#0d1117;color:#fff;'
        f'padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;'
        f'text-decoration:none;margin-top:10px;">View on GitHub →</a>'
        if github_url else ''
    )

    return (
        f'<div style="background:#fff;border:1px solid #e1e4e8;border-radius:8px;'
        f'padding:18px 22px;margin-bottom:10px;">'
        f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;">'
        f'{rank_badge}'
        f'<div style="flex:1;">{name_html}{meta_html}</div>'
        f'</div>'
        f'{body_html}'
        f'{button_html}'
        f'</div>'
    )


def _render_theme_section(content: str) -> str:
    body = _body_to_html(content.strip())
    return (
        f'<div style="background:#f0fff4;border:1px solid #bcf0c0;border-radius:8px;'
        f'padding:18px 22px;margin-top:6px;">'
        f'<h3 style="margin:0 0 10px;font-size:15px;color:#1a1a1a;">📊 This Week\'s Theme</h3>'
        f'{body}'
        f'</div>'
    )


def _build_html(brief_md: str, brief_date: str) -> str:
    # Split on ### boundaries to get individual sections
    raw_sections = re.split(r'\n(?=### )', brief_md)

    intro_block = raw_sections[0]  # "## 🚀..." heading + teaser sentence
    repo_cards_html = ""
    theme_html = ""

    for sec in raw_sections[1:]:
        content = sec[4:] if sec.startswith('### ') else sec  # strip leading "### "
        if content.startswith('📊') or content.lower().startswith("this week"):
            theme_html = _render_theme_section(
                re.sub(r'^[^\n]+\n', '', content, count=1).strip()
            )
        else:
            repo_cards_html += _render_repo_card(content)

    # Extract the teaser sentence (line after the ## heading)
    teaser = ""
    for line in intro_block.split('\n'):
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            teaser = stripped
            break

    teaser_html = (
        f'<p style="margin:6px 0 0;color:rgba(255,255,255,0.75);font-size:13px;">{teaser}</p>'
        if teaser else ''
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f6f8fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;font-size:14px;color:#1a1a1a;">
  <div style="max-width:640px;margin:32px auto;background:#f6f8fa;">

    <div style="background:#0d1117;border-radius:8px 8px 0 0;padding:24px 28px;">
      <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">🚀 GitHub Trending</h1>
      <p style="margin:2px 0 0;color:rgba(255,255,255,0.5);font-size:12px;">Top 10 repos · Week of {brief_date}</p>
      {teaser_html}
    </div>

    <div style="padding:14px 0;">
      {repo_cards_html}
      {theme_html}
    </div>

    <div style="background:#fff;border:1px solid #e1e4e8;border-radius:0 0 8px 8px;padding:14px 22px;text-align:center;">
      <p style="margin:0;font-size:11px;color:#888;">Generated by GitHub Trending Pulse &middot; Powered by Claude</p>
    </div>

  </div>
</body>
</html>"""


def send_brief(brief_md: str, brief_date: str) -> None:
    html = _build_html(brief_md, brief_date)
    subject = f"🚀 GitHub Trending — Week of {brief_date}"

    response = resend.Emails.send({
        "from":    FROM_EMAIL,
        "to":      [TO_EMAIL],
        "subject": subject,
        "html":    html,
    })

    logger.info(f"email.sent id={response.id} to={TO_EMAIL}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from datetime import date

    sample = """## 🚀 GitHub Trending — 2026-05-25

An exciting week dominated by AI tooling and Rust-based systems utilities.

### #1. anthropics/claude-engineer ⭐ 9,412 · Python
https://github.com/anthropics/claude-engineer

**What it does:** An open-source CLI that wraps Claude's API into an autonomous coding agent — you describe what to build and it writes, runs, and iterates on code in a sandboxed environment until tests pass.

**Why it's interesting:** Unlike GitHub Copilot (autocomplete), this operates at the task level: it reads your codebase, proposes a plan, writes the code, runs it, reads the error, and fixes it — all without human intervention between steps.

**Who it's for:** Backend engineers who want to automate boilerplate-heavy tasks like writing database migrations, API clients, or test suites.

### #2. zig-lang/zig ⭐ 4,200 · Zig
https://github.com/zig-lang/zig

**What it does:** A general-purpose compiled systems language designed to replace C — no hidden allocations, no undefined behavior, and a compile-time execution model that eliminates entire classes of runtime bugs.

**Why it's interesting:** The 0.14 release ships a self-hosted compiler (Zig now compiles itself), cutting compile times by 40% and removing the C bootstrap dependency entirely.

**Who it's for:** Systems programmers who find Rust's borrow checker too restrictive but still want memory-safe alternatives to C.

## 📊 This Week's Theme
This week's trending repos split cleanly into two camps: AI-augmented developer tooling (agents, code generators, prompt frameworks) and low-level systems runtimes (new languages, async I/O libraries, WebAssembly runtimes). The common thread is developer productivity at both extremes — abstracting away complexity at the top, and eliminating runtime overhead at the bottom.
"""

    send_brief(sample, str(date.today()))
