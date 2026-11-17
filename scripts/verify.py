"""Validate local document links, assignment structure and diagram artifacts."""

from pathlib import Path
import re
import struct
import unicodedata
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def anchors(text):
    result, used = set(), {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
        slug = re.sub(r"\s", "-", heading.lower())
        slug = "".join(c for c in slug if c in "-_" or not unicodedata.category(c).startswith(("P", "S")))
        count = used.get(slug, 0)
        used[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def main():
    errors, links = [], 0
    documents = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "diagrams/README.md"]
    for document in documents:
        if not document.is_file():
            errors.append(f"Missing document: {document.relative_to(ROOT)}")
            continue
        body = document.read_text(encoding="utf-8")
        for href in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", body):
            target = urlsplit(href.strip("<>"))
            if target.scheme or target.netloc:
                continue
            links += 1
            path = (document.parent / unquote(target.path)).resolve() if target.path else document
            if not path.is_file():
                errors.append(f"{document.name}: missing {href}")
            elif target.fragment and path.suffix == ".md":
                if unquote(target.fragment) not in anchors(path.read_text(encoding="utf-8")):
                    errors.append(f"{document.name}: missing anchor {href}")

    rfc = (ROOT / "docs/02-rfc.md").read_text(encoding="utf-8")
    for title in ("Контекст", "Продуктовый анализ", "Пользовательские сценарии", "Статистика", "Требования", "Варианты решения", "Сравнительный анализ", "Выводы", "Связанные задачи", "Приложения"):
        if f"## {title}\n" not in rfc:
            errors.append(f"RFC section missing: {title}")
    requirements = (ROOT / "docs/01-requirements.md").read_text(encoding="utf-8")
    for prefix, minimum in (("FR", 5), ("NFR", 5), ("ASR", 3)):
        count = len(set(re.findall(rf"\b{prefix}-\d{{2}}\b", requirements)))
        if count < minimum:
            errors.append(f"Insufficient {prefix}: {count}")

    names = [f"{option}-{kind}" for option in "ab" for kind in ("container", "normal", "failover")]
    for name in names:
        base = ROOT / "diagrams" / name
        source = base.with_suffix(".puml").read_text(encoding="utf-8")
        if source.count("@startuml") != 1 or source.count("@enduml") != 1:
            errors.append(f"Unbalanced PlantUML: {name}")
        for include in re.findall(r"^!include\s+(.+)$", source, re.M):
            if not (base.parent / include.strip()).is_file():
                errors.append(f"Missing PlantUML include: {include}")
        root = ET.parse(base.with_suffix(".svg")).getroot()
        if not root.tag.endswith("svg") or "Syntax Error" in "".join(root.itertext()):
            errors.append(f"Invalid SVG: {name}")
        png = base.with_suffix(".png").read_bytes()
        if png[:8] != b"\x89PNG\r\n\x1a\n" or min(struct.unpack(">II", png[16:24])) < 100:
            errors.append(f"Invalid PNG: {name}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"OK: {len(documents)} documents, {links} local links, RFC sections, requirement IDs, {len(names)} diagrams (PlantUML/SVG/PNG).")


if __name__ == "__main__":
    main()
