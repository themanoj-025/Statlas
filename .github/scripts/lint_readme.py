#!/usr/bin/env python3
"""Lint README.md: heading anchors, relative links, heading levels, code fences.

Checks (stdlib only, no dependencies):
  1. Every internal anchor (#...) resolves to a real heading slug (GitHub rules).
  2. Every relative link target exists; fragments on .md targets are verified too.
  3. Heading levels never jump more than one level deeper (a11y).
  4. Every fenced code block opens with a language tag.
  5. All fences are balanced (no unterminated blocks).

Exit codes: 0 = clean, 1 = violations found (printed with line numbers).
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_HEADING_RE = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE)


def github_slug(text: str) -> str:
    """Match github-slugger: lowercase, keep letters/numbers/marks/space/-/_."""
    text = text.strip().lower()
    out = []
    for ch in text:
        if ch in (" ", "-", "_"):
            out.append(ch)
        else:
            cat = unicodedata.category(ch)
            if cat[0] in ("L", "N", "M"):
                out.append(ch)
    return "".join(out).replace(" ", "-")


def strip_md(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def collect_slugs(lines: list[str]) -> dict[str, int]:
    slugs: dict[str, int] = {}
    fence_char, fence_len = "", 0
    for line in lines:
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not fence_char:
                fence_char, fence_len = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                fence_char = ""
            continue
        if fence_char:
            continue
        m = HEADING_RE.match(line)
        if m:
            title = strip_md(m.group(2))
        else:
            m2 = HTML_HEADING_RE.search(line)
            if not m2:
                continue
            title = strip_md(m2.group(2))
        slug = github_slug(title)
        base, n = slug, 1
        while slug in slugs:
            slug = f"{base}-{n}"
            n += 1
        slugs[slug] = 0
    return slugs


def lint(path: Path) -> list[str]:
    problems: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    slugs = collect_slugs(lines)

    fence_char, fence_len = "", 0
    prev_level = 0

    for no, line in enumerate(lines, start=1):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not fence_char:
                fence_char, fence_len = marker[0], len(marker)
                info = m.group(2).strip()
                if not info:
                    problems.append(f"{path}:{no}: code fence missing language tag")
            elif marker[0] == fence_char and len(marker) >= fence_len:
                fence_char = ""
            continue
        if fence_char:
            continue

        for _text, target in LINK_RE.findall(re.sub(r"`[^`]*`", "", line)):
            if target.startswith(("http://", "https://", "mailto:", "#")) or not target:
                fragment = target[1:] if target.startswith("#") else None
                if fragment and fragment not in slugs:
                    problems.append(f"{path}:{no}: broken anchor #{fragment}")
                continue
            frag = None
            rel = target
            if "#" in target:
                rel, _, frag = target.partition("#")
            if rel:
                if (path.parent / rel).exists():
                    if frag and rel.lower().endswith(".md"):
                        md_slugs = collect_slugs(
                            (path.parent / rel).read_text(encoding="utf-8").splitlines()
                        )
                        if frag and frag not in md_slugs:
                            problems.append(f"{path}:{no}: broken anchor {target}")
                else:
                    problems.append(f"{path}:{no}: relative target not found: {rel}")

        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            if prev_level and level > prev_level + 1:
                problems.append(f"{path}:{no}: heading jump h{prev_level}->h{level}")
            prev_level = level

    if fence_char:
        problems.append(
            f"{path}: unterminated fenced code block (opened with {fence_char * fence_len})"
        )
    return problems


def main() -> int:
    root = Path(".")
    targets = [root / "README.md"]
    docs = sorted((root / "docs").rglob("*.md")) if (root / "docs").is_dir() else []
    exit_code = 0
    for doc in [t for t in targets if t.exists()] + docs:
        for problem in lint(doc):
            print(problem)
            exit_code = 1
    if exit_code == 0:
        print(f"README lint OK ({1 + len(docs)} file(s) checked)")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
