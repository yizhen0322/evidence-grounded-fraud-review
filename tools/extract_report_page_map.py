"""Extract printed main-matter page numbers for report headings and captions."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def candidates(markdown: Path) -> list[str]:
    values: list[str] = []
    in_mainmatter = False
    for raw in markdown.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "<!-- mainmatter -->":
            in_mainmatter = True
            continue
        if in_mainmatter:
            heading = re.match(r"^#{1,3}\s+(.+)$", line)
            if heading:
                values.append(heading.group(1).strip())
        table = re.match(r"^(Table (?:\d+(?:\.\d+)?|[A-Z]\.\d+)\..+)$", line)
        if table:
            values.append(table.group(1).strip())
        figure = re.match(r"^!\[(Figure \d+\.\d+\.[^]]+)]\(.+\)$", line)
        if figure:
            caption = figure.group(1).strip()
            values.append(caption)
            values.append(caption.split(". ", 1)[0] + ". " + caption.split(". ", 1)[1].split(". ", 1)[0])
    return list(dict.fromkeys(values))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown", type=Path)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".txt") as text_file:
        subprocess.run(
            ["pdftotext", "-layout", str(args.pdf.resolve()), text_file.name],
            check=True,
        )
        pages = Path(text_file.name).read_text(encoding="utf-8", errors="replace").split("\f")

    normalized_pages = [normalize(page) for page in pages]
    intro_physical = next(
        index
        for index, page in enumerate(pages, start=1)
        if re.search(r"(?m)^\s*1\. Introduction\s*$", page)
    )
    result: dict[str, int] = {}
    for value in candidates(args.markdown.resolve()):
        needle = normalize(value)
        # Long captions may wrap or be shortened in the List of Figures. Match
        # the stable caption label and first descriptive clause when needed.
        fallback = normalize(". ".join(value.split(". ")[:2]))
        for physical, page in enumerate(normalized_pages, start=1):
            if needle in page or (fallback and fallback in page):
                if physical >= intro_physical:
                    result[value] = physical - intro_physical + 1
                    break

    # Front-list text is shorter than the full figure captions. Map by label.
    markdown_lines = args.markdown.read_text(encoding="utf-8").splitlines()
    for raw in markdown_lines:
        line = raw.strip()
        if line.startswith("Figure "):
            label = line.split(". ", 1)[0]
            matching = next((key for key in result if key.startswith(label + ".")), None)
            if matching:
                result[line] = result[matching]
        elif line.startswith("Table "):
            label = line.split(". ", 1)[0]
            matching = next((key for key in result if key.startswith(label + ".")), None)
            if matching:
                result[line] = result[matching]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
