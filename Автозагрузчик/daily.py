import json
import logging
import re
from collections import Counter
from contextlib import ExitStack

from playwright.sync_api import sync_playwright

from parser import parse
from scanner import scan
from studio import Studio
from rich_text import DraftContentMismatch


def remember_queue(db, cid, items):
    """Distinct from diagnostics: a dry run must never consume a future upload."""
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS daily_channels(channel TEXT PRIMARY KEY)")
        db.execute("""CREATE TABLE IF NOT EXISTS daily_sources(channel TEXT, number TEXT, historical INTEGER,
                      PRIMARY KEY(channel, number))""")
        first = not db.execute("SELECT 1 FROM daily_channels WHERE channel=?", (cid,)).fetchone()
        db.executemany("INSERT OR IGNORE INTO daily_sources VALUES(?,?,?)",
                       [(cid, item.number, int(first)) for item in items if not item.hold])
        db.execute("INSERT OR IGNORE INTO daily_channels VALUES(?)", (cid,))
    return {r[0] for r in db.execute("SELECT number FROM daily_sources WHERE channel=? AND historical=1", (cid,))}


def finish(journal, studio, cid, item, article, url, resume):
    try:
        studio.write(url, article, resume)
        journal.verified(cid, item.number, url)
    except Exception as exc:
        with journal.db:
            journal.db.execute("UPDATE publications SET error=? WHERE channel=? AND number=?",
                               (str(exc), cid, item.number))
        raise


def run_channel(root, state, journal, channel, context, lines):
    cid = channel["id"]
    counts = Counter()
    items = scan(root, channel)
    old = remember_queue(journal.db, cid, items)
    studio = None
    for item in items:
        row = journal.row(cid, item.number)
        status = row["status"] if row else None
        if item.recorded or status in ("verified", "matched"):
            counts["дубли"] += 1
            continue
        if status == "draft_review":
            counts["проверить"] += 1
            lines.append(f"№ {item.number}: проверьте существующий черновик {row['draft_url']}")
            continue
        if item.number in old and status not in ("approved", "pending"):
            continue
        if item.hold:
            counts["проверить"] += 1
            continue
        counts["новые"] += 1
        try:
            article = parse(item.path.read_text(encoding="utf-8-sig"), keep_prompts=True)
            row = journal.observe(cid, item, article, item.path.relative_to(root).as_posix())
            if article.images:
                dest = state / "images" / cid / (item.number+".json")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps({"title": article.title, "images": article.images},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
            if studio is None:
                studio = Studio(context, channel, state)
            url = row["draft_url"] if row["status"] == "pending" else None
            if url:
                if row["digest"] != article.digest:
                    raise ValueError("Исходник изменился после начала ввода. Проверьте черновик.")
                studio.page.goto(url, wait_until="domcontentloaded")
            else:
                menu = studio.open_menu()
                with journal.db:
                    journal.db.execute("UPDATE publications SET status='pending', digest=? WHERE channel=? AND number=?",
                                       (article.digest, cid, item.number))
                url = studio.create(menu)
                with journal.db:
                    journal.db.execute("UPDATE publications SET draft_url=? WHERE channel=? AND number=?",
                                       (url, cid, item.number))
            finish(journal, studio, cid, item, article, url, bool(row["draft_url"]))
            counts["создано"] += 1
            lines.append(f"Сохранён № {item.number} «{article.title}»: {url}")
            print(lines[-1], flush=True)
        except DraftContentMismatch as exc:
            with journal.db:
                journal.db.execute("UPDATE publications SET status='draft_review',error=? WHERE channel=? AND number=?",
                                   (str(exc), cid, item.number))
            counts["проверить"] += 1
            lines.append(f"№ {item.number}: {exc}. {url}")
        except Exception as exc:
            counts["ошибки"] += 1
            lines.append(f"№ {item.number}: {exc}")
            logging.exception("Материал %s/%s", cid, item.number)
            if channel["source"] == "queue":
                break
    return counts


def upload(root, channels, state, journal, revision):
    report = [f"Снимок {revision}"]
    failed = False
    with sync_playwright() as pw, ExitStack() as stack:
        contexts = {}
        for channel in sorted(channels, key=lambda c:c["id"]!="barskaya"):
            name = channel["name"]
            if not channel.get("studio_url") or channel.get("enabled") is False:
                report.append(f"{name}: выключен")
                continue
            print(f"Канал «{name}»", flush=True)
            details = []
            try:
                profile = channel["profile"]
                if not re.fullmatch(r"[A-Za-z0-9_-]+",profile):
                    raise ValueError("Проверьте имя профиля")
                if profile not in contexts:
                    ctx = pw.chromium.launch_persistent_context(str(state/"profiles"/profile),
                                                               headless=False,locale="ru-RU")
                    contexts[profile] = ctx
                    stack.callback(ctx.close)
                counts = run_channel(root,state,journal,channel,contexts[profile],details)
                failed |= bool(counts["ошибки"])
                summary = name+" — "+", ".join(f"{k}: {counts[k]}" for k in ("новые","создано","дубли","проверить","ошибки"))
            except Exception as exc:
                failed = True
                logging.exception("Канал %s",name)
                summary = f"{name}: остановлен — {exc}"
            report.extend([summary,*details,""])
            print(summary,flush=True)
            (state/"last-report.txt").write_text("\n".join(report), encoding="utf-8-sig")
    return int(failed)
