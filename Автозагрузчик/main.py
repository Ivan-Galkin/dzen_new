import argparse
import json
import logging
import os
import re
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing, contextmanager
from pathlib import Path

from dzen_browser import login
from parser import parse
from repository import snapshot
from scanner import scan
from storage import Journal, normalize

MODULE = Path(__file__).resolve().parent


@contextmanager
def lock(state):
    # Windows and SQLite release the exclusive lock on process death.
    with closing(sqlite3.connect(state / "lock.sqlite", timeout=0)) as connection:
        try:
            connection.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError as exc:
            raise RuntimeError("Другой экземпляр уже работает") from exc
        yield


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8-sig")
    temporary.replace(path)


def diagnose(root, channels, state, journal, revision):
    report = ["Снимок исходников " + revision]
    errors = 0
    for channel in channels:
        lines, counts = [], Counter()
        cid = channel["id"]
        try:
            items = scan(root, channel)
        except (OSError, UnicodeError, ValueError) as exc:
            items = []
            counts["ошибки"] += 1
            lines.append(str(exc))
            logging.exception("Реестр %s", cid)
        for item in items:
            try:
                article = parse(item.path.read_text(encoding="utf-8-sig"), keep_prompts=True)
                row = journal.observe(cid, item, article, item.path.relative_to(root).as_posix())
                if item.recorded or row["status"] in ("matched", "verified"):
                    status, reason = "дубли", "отметка реестра или журнала"
                elif item.hold:
                    status, reason = "проверить", item.hold
                elif row["status"] in ("approved", "pending"):
                    status, reason = "новые", "в очереди на создание или повторную попытку"
                else:
                    initialized = journal.db.execute("SELECT 1 FROM sqlite_master WHERE name='daily_channels'").fetchone()
                    initialized = initialized and journal.db.execute("SELECT 1 FROM daily_channels WHERE channel=?", (cid,)).fetchone()
                    historical = initialized and journal.db.execute("SELECT 1 FROM daily_sources WHERE channel=? AND number=? AND historical=1", (cid,item.number)).fetchone()
                    if initialized and not historical:
                        status, reason = "новые", "готовый номер появился после первого запуска"
                    else:
                        status, reason = "архив", "номер исходного снимка"
                lines.append(f"{item.number}. {article.title} — {status}: {reason}")
                counts[status] += 1
                if row["draft_url"]:
                    lines.append(row["draft_url"])
                if article.warnings:
                    lines.append("Заполнить вручную: " + ", ".join(article.warnings))
                if article.images:
                    data = {"title": article.title, "images": article.images}
                    save(state / "images" / cid / (item.number + ".json"),
                         json.dumps(data, ensure_ascii=False, indent=2))
                # Render the exact HTML intended for the editor during diagnosis.
                from html import escape
                save(state / "preview" / cid / (item.number + ".html"),
                     """<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'"><h1>"""
                     + escape(article.title) + "</h1>\n" + article.html())
            except (ValueError, UnicodeError, OSError) as exc:
                counts["ошибки"] += 1
                lines.append(f"{item.number}. {item.path.name} — {exc}")
                logging.exception("Материал %s/%s", cid, item.number)
        summary = (f"{channel['name']} — в источнике {len(items)}, новых в очереди {counts['новые']}, "
                   f"создано 0, дубли {counts['дубли']}, проверить {counts['проверить']}, ошибки {counts['ошибки']}")
        report.append(summary)
        if channel.get("studio_url"):
            report.append("Адрес Студии для сверки: " + channel["studio_url"])
        report.extend([*lines, ""])
        print(summary)
        errors += counts["ошибки"]
    save(state / "last-report.txt", "\n".join(report))
    print("Отчёт:", state / "last-report.txt")
    return errors


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("mode", choices=["check", "run", "login"])
    cli.add_argument("--snapshot", type=Path, help="Диагностика сохранённой копии без сети")
    cli.add_argument("--state", type=Path)
    cli.add_argument("--profile", default="main")
    args = cli.parse_args()
    state = args.state or Path(os.environ["LOCALAPPDATA"]) / "DzenDraftLoader"
    state.mkdir(parents=True, exist_ok=True)
    with lock(state):
        logging.basicConfig(filename=state / "technical.log", encoding="utf-8", level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
        config = state / "config.json"
        channels = json.loads((config if config.exists() else MODULE / "config.example.json")
                              .read_text(encoding="utf-8-sig"))["channels"]
        defaults = json.loads((MODULE / "config.example.json").read_text(encoding="utf-8-sig"))
        urls = {c["id"]: c["studio_url"] for c in defaults["channels"] if c.get("studio_url")}
        for channel in channels:
            if channel["id"] in urls:
                channel.setdefault("studio_url", urls[channel["id"]])
            default = next((c for c in defaults["channels"] if c["id"] == channel["id"]), {})
            if default.get("editor_channel_id"):
                channel.setdefault("editor_channel_id", default["editor_channel_id"])
        ids = [c["id"] for c in channels]
        if len(set(ids)) != len(ids) or not all(re.fullmatch(r"[a-z0-9_-]+", cid) for cid in ids):
            raise ValueError("Идентификаторы каналов должны быть уникальными")
        if args.mode == "login":
            if args.profile not in {c["profile"] for c in channels}:
                raise ValueError("Профиль отсутствует в config.json")
            login(state, args.profile)
            return 0
        if args.snapshot and args.mode != "check":
            raise ValueError("--snapshot допускается только в диагностике")
        with tempfile.TemporaryDirectory() as directory:
            root = args.snapshot or Path(directory)
            revision = "локальная копия" if args.snapshot else snapshot(state, root, {c["folder"] for c in channels})
            journal = Journal(state / "publications.sqlite")
            with closing(journal.db):
                if args.mode == "run":
                    from daily import upload
                    return upload(root, channels, state, journal, revision)
                errors = diagnose(root, channels, state, journal, revision)
        return int(bool(errors))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logging.exception("Запуск остановлен")
        print("Запуск остановлен:", error)
        raise SystemExit(1)
