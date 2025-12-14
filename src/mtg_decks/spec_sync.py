"""Utilities for keeping the functional spec markdown and HTML in sync."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

import html
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MD_PATH = PROJECT_ROOT / "FUNCTIONAL_SPEC.md"
DEFAULT_HTML_PATH = PROJECT_ROOT / "functional-spec.html"
DEFAULT_ERROR_LOG = PROJECT_ROOT / "error.log"


STYLE_BLOCK = """
    :root {
      color-scheme: dark;
      --bg: #04060a;
      --panel: #0d1017;
      --border: #1c1f27;
      --accent: #71c9f8;
      --accent-strong: #9ae7ff;
      --text: #f1f5ff;
      --muted: #a4b3cc;
      --shadow: 0 14px 36px rgba(0, 0, 0, 0.38);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(circle at 12% 14%, rgba(113, 201, 248, 0.12), transparent 25%),
        radial-gradient(circle at 82% -6%, rgba(154, 231, 255, 0.12), transparent 22%),
        var(--bg);
      color: var(--text);
      font-family: "Inter", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.65;
      padding: 32px 16px 48px;
    }

    a {
      color: var(--accent);
      text-decoration: none;
    }

    a:hover,
    a:focus-visible {
      color: var(--accent-strong);
    }

    .page {
      max-width: 1100px;
      margin: 0 auto;
      display: grid;
      gap: 18px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border);
      padding: 12px 16px;
      border-radius: 12px;
    }

    .brand {
      font-weight: 700;
      letter-spacing: 0.3px;
    }

    .nav {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .button {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.02);
      color: var(--text);
      text-decoration: none;
      font-weight: 600;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }

    .button:hover,
    .button:focus-visible {
      transform: translateY(-1px);
      border-color: #2a2f3b;
      background: rgba(113, 201, 248, 0.08);
    }

    header.hero {
      background: linear-gradient(135deg, rgba(113, 201, 248, 0.14), rgba(6, 8, 12, 0.7)), var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: var(--shadow);
      display: grid;
      gap: 12px;
    }

    .hero h1 {
      margin: 0;
      font-size: clamp(1.9rem, 2.9vw + 1rem, 2.7rem);
    }

    .hero p {
      margin: 0;
      color: var(--muted);
      max-width: 820px;
    }

    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .pill {
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.02);
      padding: 7px 10px;
      border-radius: 999px;
      color: var(--muted);
      font-weight: 600;
      font-size: 0.95rem;
    }

    .card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      box-shadow: var(--shadow);
      display: grid;
      gap: 14px;
    }

    .columns {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }

    .toc h2 {
      margin: 0 0 6px 0;
    }

    .toc ul {
      list-style: none;
      padding-left: 0;
      margin: 0;
      display: grid;
      gap: 6px;
    }

    .toc li {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.02);
    }

    .spec-content h2,
    .spec-content h3 {
      margin-top: 18px;
      margin-bottom: 10px;
    }

    .spec-content table {
      width: 100%;
      border-collapse: collapse;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
    }

    .spec-content th,
    .spec-content td {
      padding: 10px;
      border-bottom: 1px solid var(--border);
    }

    .spec-content tr:last-child td {
      border-bottom: none;
    }

    @media (max-width: 900px) {
      .columns {
        grid-template-columns: 1fr;
      }
    }
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>MTG Decks – Functional Spec</title>
  <style>
{styles}
  </style>
</head>
<body>
  <div class=\"page\">
    <div class=\"topbar\">
      <div class=\"brand\">MTG Decks</div>
      <div class=\"nav\">
        <a class=\"button\" href=\"index.html\">Home</a>
        <a class=\"button\" href=\"decks.html\">Deck Browser</a>
        <a class=\"button\" href=\"inventory.html\">Inventory</a>
        <a class=\"button\" href=\"valuation-report.md\">Valuation report</a>
      </div>
    </div>

    <header class=\"hero\">
      <h1>Functional Specification</h1>
      <p>A single source of truth for MTG-Decks requirements, CLI behavior, and data contracts. This HTML is generated from FUNCTIONAL_SPEC.md to keep both formats aligned.</p>
      <div class=\"pill-row\">
        <div class=\"pill\">Markdown + HTML parity</div>
        <div class=\"pill\">Deck + inventory coverage</div>
        <div class=\"pill\">CI-verified</div>
      </div>
    </header>

    <div class=\"columns\">
      <aside class=\"card toc\">
        <h2>Contents</h2>
        {toc}
      </aside>
      <main class=\"card spec-content\">{content}</main>
    </div>
  </div>
</body>
</html>
"""


class SimpleMarkdown:
    """Lightweight markdown-to-HTML converter to avoid external runtime dependencies."""

    def __init__(self) -> None:
        self._toc: list[tuple[int, str, str]] = []

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return slug or "section"

    @staticmethod
    def _inline(text: str) -> str:
        def replace_code(match: re.Match[str]) -> str:
            return f"<code>{html.escape(match.group(1))}</code>"

        def replace_strong(match: re.Match[str]) -> str:
            return f"<strong>{html.escape(match.group(1))}</strong>"

        escaped = html.escape(text)
        escaped = re.sub(r"`([^`]+)`", replace_code, escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", replace_strong, escaped)
        return escaped

    def _flush_paragraph(self, buffer: list[str], output: list[str]) -> None:
        if buffer:
            output.append(f"<p>{' '.join(buffer)}</p>")
            buffer.clear()

    def _flush_list(self, in_list: bool, output: list[str]) -> bool:
        if in_list:
            output.append("</ul>")
        return False

    def _flush_table(self, table_lines: list[str], output: list[str]) -> None:
        if not table_lines:
            return

        rows = [row.strip().strip("|") for row in table_lines if row.strip()]
        if not rows:
            return

        header_cells = [cell.strip() for cell in rows[0].split("|")]
        data_rows = rows[1:]
        # Drop alignment row when present (second row filled with dashes/colons)
        if data_rows and re.fullmatch(r"[:\-\s|]+", table_lines[1]):
            data_rows = rows[2:]

        output.append("<table>")
        output.append("  <thead><tr>" + "".join(f"<th>{self._inline(cell)}</th>" for cell in header_cells) + "</tr></thead>")
        if data_rows:
            output.append("  <tbody>")
            for row in data_rows:
                cells = [cell.strip() for cell in row.split("|")]
                output.append("    <tr>" + "".join(f"<td>{self._inline(cell)}</td>" for cell in cells) + "</tr>")
            output.append("  </tbody>")
        output.append("</table>")
        table_lines.clear()

    def convert(self, markdown_text: str) -> str:
        output: list[str] = []
        paragraph_buffer: list[str] = []
        table_buffer: list[str] = []
        in_list = False

        lines = markdown_text.splitlines()
        for idx, line in enumerate(lines + [""]):
            heading = re.match(r"^(#{1,6})\s+(.*)", line)
            is_table_row = line.strip().startswith("|") and line.strip().endswith("|")

            if heading:
                self._flush_table(table_buffer, output)
                self._flush_paragraph(paragraph_buffer, output)
                in_list = self._flush_list(in_list, output)

                level = len(heading.group(1))
                title = heading.group(2).strip()
                anchor = self._slugify(title)
                self._toc.append((level, title, anchor))
                output.append(f"<h{level} id=\"{anchor}\">{self._inline(title)}</h{level}>")
                continue

            if is_table_row:
                table_buffer.append(line)
                continue

            if table_buffer and not is_table_row:
                self._flush_table(table_buffer, output)

            if line.startswith("- "):
                self._flush_paragraph(paragraph_buffer, output)
                if not in_list:
                    output.append("<ul>")
                    in_list = True
                output.append(f"  <li>{self._inline(line[2:].strip())}</li>")
                continue

            if in_list and line.strip() == "":
                in_list = self._flush_list(in_list, output)
                continue

            if line.strip() == "":
                self._flush_paragraph(paragraph_buffer, output)
                continue

            paragraph_buffer.append(self._inline(line.strip()))

        self._flush_table(table_buffer, output)
        self._flush_paragraph(paragraph_buffer, output)
        if in_list:
            self._flush_list(in_list, output)

        return "\n".join(output)

    def toc(self) -> str:
        items = [f'<li><a href="#{anchor}">{html.escape(title)}</a></li>' for _, title, anchor in self._toc]
        return "<ul>" + "".join(items) + "</ul>"


def render_spec_html(markdown_text: str) -> str:
    """Convert markdown text to a styled HTML document."""

    md = SimpleMarkdown()
    content_html = md.convert(markdown_text)
    toc_html = md.toc()
    return HTML_TEMPLATE.format(styles=STYLE_BLOCK, toc=toc_html, content=content_html)


def normalize_markdown(markdown_text: str) -> str:
    """Normalize markdown for consistent serialization."""

    return markdown_text.rstrip() + "\n"


def write_error(message: str, error_log: Path = DEFAULT_ERROR_LOG) -> None:
    """Append an error message to the configured error log."""

    existing = error_log.read_text(encoding="utf-8") if error_log.exists() else ""
    error_log.write_text(f"{existing}{message}\n", encoding="utf-8")


def spec_is_in_sync(
    md_path: Path = DEFAULT_MD_PATH,
    html_path: Path = DEFAULT_HTML_PATH,
    error_log: Path = DEFAULT_ERROR_LOG,
) -> bool:
    """Check whether the HTML spec matches the markdown source, logging when it does not."""

    markdown_text = md_path.read_text(encoding="utf-8")
    generated_html = render_spec_html(markdown_text)
    current_html = html_path.read_text(encoding="utf-8")

    if generated_html != current_html:
        write_error("functional-spec.html is out of sync with FUNCTIONAL_SPEC.md", error_log)
        return False

    return True


def rewrite_markdown(md_path: Path = DEFAULT_MD_PATH) -> None:
    """Rewrite the markdown file to ensure consistent newlines and formatting."""

    current_text = md_path.read_text(encoding="utf-8")
    md_path.write_text(normalize_markdown(current_text), encoding="utf-8")


def regenerate_html(md_path: Path = DEFAULT_MD_PATH, html_path: Path = DEFAULT_HTML_PATH) -> None:
    """Regenerate the HTML artifact from markdown."""

    html_path.write_text(render_spec_html(md_path.read_text(encoding="utf-8")), encoding="utf-8")


def parse_args(args: Optional[list[str]] = None) -> ArgumentParser:
    parser = ArgumentParser(description="Keep FUNCTIONAL_SPEC.md and functional-spec.html aligned.")
    parser.add_argument("--md", type=Path, default=DEFAULT_MD_PATH, help="Path to the markdown source.")
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML_PATH, help="Path to the rendered HTML output.")
    parser.add_argument("--error-log", type=Path, default=DEFAULT_ERROR_LOG, help="Path to the error log file.")
    parser.add_argument("--rewrite-md", action="store_true", help="Rewrite the markdown file with normalized whitespace.")
    parser.add_argument("--write", action="store_true", help="Regenerate the HTML artifact from markdown.")
    parser.add_argument("--check", action="store_true", help="Verify the HTML matches markdown, logging mismatches.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = parse_args()
    options = parser.parse_args(argv)

    if options.rewrite_md:
        rewrite_markdown(options.md)

    if options.write:
        regenerate_html(options.md, options.html)

    if options.check:
        return 0 if spec_is_in_sync(options.md, options.html, options.error_log) else 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
