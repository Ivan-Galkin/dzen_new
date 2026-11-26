import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Item:
    number: str
    kind: str
    path: Path
    title: str = ""
    hold: str = ""
    recorded: bool = False


def rows(path):
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        cells = [v.strip() for v in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells[0].isdigit():
            yield cells


def scan(root, channel):
    base = root / channel["folder"]
    if not base.is_dir():
        raise ValueError(f"Отсутствует папка {base.name}")
    source = channel["source"]
    items = []
    if source == "queue":
        previous = 0
        for cells in rows(base / "ВЫКЛАДКА.md"):
            n, kind, status, out, title, file = cells
            number = int(n)
            if number != previous + 1:
                raise ValueError("Нарушена сквозная нумерация очереди")
            previous = number
            if status.casefold() == "резерв снят" and file == "(не написано)":
                continue
            if status.casefold() != "готово":
                break
            legacy_name = number <= 44 and re.fullmatch(r"(Рассказ|Рецепт|Кухни)-\d+_ГОТОВО-К-ВСТАВКЕ\.md", file)
            unified_name = file == f"Публикация-{number:02d}_ГОТОВО-К-ВСТАВКЕ.md"
            if not (legacy_name or unified_name):
                raise ValueError(f"Неизвестный файл публикации {n}")
            items.append(Item(n, kind.split()[0], base / file, title, recorded=bool(out)))
    elif source == "marketing":
        for n, file, title, status, date, views in rows(base / "00_НАЧНИ-ОТСЮДА.md"):
            file = file.strip(chr(96))
            match = re.fullmatch(r"Статьи/Статья-(\d+)_[^/\\]+\.md", file)
            if not match or int(match[1]) != int(n):
                raise ValueError(f"Проверьте строку реестра {n}")
            ready = re.search(r"\bготов[ао]?\b", status, re.I)
            hold = "" if ready and not re.search(r"жд[её]т|вычитк|доработ|не готов", status, re.I) else status or "Нет статуса"
            items.append(Item(str(int(n)), "статья", base / file, title, hold, bool(date.strip())))
    elif source in ("history", "stories"):
        prefix = "Статья" if source == "history" else "Рассказ"
        ext = "md|txt" if source == "history" else "md"
        pattern = re.compile(fr"{prefix}-(\d+(?:-\d+)?)_ГОТОВО-К-ВСТАВКЕ\.({ext})")
        for path in base.iterdir():
            m = pattern.fullmatch(path.name)
            if m:
                number = "-".join(str(int(part)) for part in m[1].split("-"))
                items.append(Item(number, prefix.lower(), path))
    else:
        raise ValueError(f"Неизвестный источник {source}")
    if len({x.number for x in items}) != len(items) or len({x.path for x in items}) != len(items):
        raise ValueError("Повтор номера или файла в реестре")
    return sorted(items, key=lambda x: tuple(map(int, x.number.split("-"))))
