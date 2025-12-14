from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Deck:
    """Representation of a Commander deck stored as a Markdown file."""

    name: str
    commander: str
    colors: list[str] = field(default_factory=list)
    theme: Optional[str] = None
    format: str = "Commander"
    created: Optional[str] = None
    updated: Optional[str] = None
    notes: Optional[str] = None
    path: Optional[Path] = None

    FRONT_MATTER_MARK = "---"

    def to_markdown(self) -> str:
        front_matter = [self.FRONT_MATTER_MARK]
        front_matter.append(f"name: {self.name}")
        front_matter.append(f"commander: {self.commander}")
        if self.colors:
            front_matter.append(f"colors: {', '.join(self.colors)}")
        if self.theme:
            front_matter.append(f"theme: {self.theme}")
        if self.format:
            front_matter.append(f"format: {self.format}")
        if self.created:
            front_matter.append(f"created: {self.created}")
        if self.updated:
            front_matter.append(f"updated: {self.updated}")
        if self.notes:
            front_matter.append(f"notes: {self.notes}")
        front_matter.append(self.FRONT_MATTER_MARK)

        body = [f"# {self.name}"]
        body.append(f"**Commander:** {self.commander}")
        if self.theme:
            body.append(f"**Theme:** {self.theme}")
        if self.colors:
            body.append(f"**Colors:** {', '.join(self.colors)}")
        body.append("\n## Decklist\n")
        body.append(f"- [Commander] {self.commander}")
        body.append("- ... add the rest of your cards here ...")

        return "\n".join(front_matter + ["\n"] + body) + "\n"

    @classmethod
    def from_file(cls, path: Path) -> "Deck":
        lines = path.read_text(encoding="utf-8").splitlines()
        metadata: dict[str, str] = {}

        if lines and lines[0].strip() == cls.FRONT_MATTER_MARK:
            for idx in range(1, len(lines)):
                line = lines[idx].strip()
                if line == cls.FRONT_MATTER_MARK:
                    break
                if line and ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()

        name = metadata.get("name") or path.stem.replace("-", " ")
        commander = metadata.get("commander", "Unknown")
        colors = _split_csv(metadata.get("colors", ""))
        theme = metadata.get("theme")
        created = metadata.get("created")
        updated = metadata.get("updated")
        notes = metadata.get("notes")
        deck_format = metadata.get("format", "Commander")

        return cls(
            name=name,
            commander=commander,
            colors=colors,
            theme=theme,
            created=created,
            updated=updated,
            format=deck_format,
            notes=notes,
            path=path,
        )


def _split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def slugify(text: str) -> str:
    """Create a file-system friendly slug."""

    slug_chars: list[str] = []
    last_dash = False
    for char in text.lower():
        if char.isalnum():
            slug_chars.append(char)
            last_dash = False
        elif char in {" ", "-", "_"}:
            if not last_dash:
                slug_chars.append("-")
                last_dash = True
    slug = "".join(slug_chars).strip("-")
    return slug or "deck"
