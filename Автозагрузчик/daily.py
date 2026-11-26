import json
import logging
import re
from collections import Counter
from contextlib import ExitStack

from playwright.sync_api import Error as BrowserError, sync_playwright

from drafts import prepare
from parser import parse
from scanner import scan
from storage import normalize
from studio import Studio


def remember_queue(db, cid, items):
    """Distinct from diagnostics: a dry run must never consume a future upload."""
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS daily_channels(channel TEXT PRIMARY KEY)")
        db.execute("""CREATE TABLE IF NOT EXISTS daily_sources(channel TEXT, number TEXT, historical INTEGER,
                      PRIMARY KEY(channel, number))""")
        first = not db.execute("SELECT 1 FROM daily_channels WHERE channel=?", (cid,)).fetchone()
        db.executemany("INSERT OR IGNORE INTO daily_sources VALUES(?,?,?)",
                       [(cid, item.number, int(first)) for item in items])
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
    entries = []
    explicit = set(map(str, channel.get("approved_numbers", [])))
    if cid == "barskaya":
        explicit.add("59")
    for item in items:
        try:
            article = parse(item.path.read_text(encoding="utf-8-sig"), keep_prompts=True)
            row = journal.observe(cid, item, article, item.path.relative_to(root).as_posix())
            entries.append((item, article))
            if row["status"] in ("verified","matched") or item.recorded:
                counts["дубли"] += 1
            if article.images:
                dest = state / "images" / cid / (item.number+".json")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps({"title":article.title, "images":article.images},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, ValueError) as exc:
            lines.append(f"{item.number}: {exc}")
            counts["ошибки"] += 1
            if channel["source"] == "queue":
                break
    pending = journal.db.execute("SELECT * FROM publications WHERE channel=? AND status='pending'",(cid,)).fetchall()
    studio = None
    current = None
    held = set()
    if pending:
        studio = Studio(context, channel, state)
        current = studio.inventory()
    for row in pending:
        number = row["number"]
        pair = next(((i,a) for i,a in entries if i.number==number and a.digest==row["digest"]), None)
        title = normalize(row["title"])
        matches = [e for e in current if normalize(e["title"]) == title]
        if len(matches) == 1 and matches[0]["status"] in ("published", "scheduled"):
            with journal.db:
                journal.db.execute("""UPDATE publications SET status='matched', draft_url=?, error=NULL
                                      WHERE channel=? AND number=? AND status='pending'""",
                                   (matches[0]["url"], cid, number))
            lines.append(f"№ {number} уже есть в Студии: {matches[0]['url']}")
            continue
        url = row["draft_url"]
        address = url.split("?")[0].split("#")[0].rstrip("/") if url else None
        if pair and address and any(e["status"]=="draft" and e["url"]==address for e in current):
            studio.page.goto(url, wait_until="domcontentloaded")
            finish(journal, studio, cid, *pair, url, True)
            lines.append(f"Подтверждён черновик № {number}: {url}")
        else:
            held.add(number)
            lines.append(f"№ {number}: незавершённая запись, повтор пропущен до сверки.")
    baseline = journal.db.execute("SELECT 1 FROM baselines WHERE channel=?", (cid,)).fetchone()
    todo = [(i,a) for i,a in entries if not i.recorded and not i.hold and (i.number not in old or i.number in explicit)
            and journal.row(cid,i.number)["status"] in ("review","approved")]
    if baseline and not todo and current is None:
        counts["проверить"] = len(entries) - counts["дубли"] - len(pending)
        lines.append("Новых материалов для загрузки нет.")
        return counts
    if studio is None:
        studio = Studio(context, channel, state)
    try:
        inventory = current if current is not None else studio.inventory()
    except (BrowserError, ValueError, AssertionError) as exc:
        # Only the owner-approved pilot follow-up can use manual first reconciliation.
        if cid != "barskaya" or not any(i.number=="59" for i,a in todo):
            raise
        print("Полный список пока не подтверждён:", exc, flush=True)
        studio.listing()
        print("Разовая сверка: проверьте «Снохин долг» в опубликованных, ожидающих и черновиках.")
        if input("Если его нигде нет, введите 59; иначе нажмите Enter: ").strip()!="59":
            raise ValueError("№ 59 оставлен на сверку")
        inventory = None
    if inventory is not None:
        approvals = [(i.number,a.digest) for i,a in entries if i.number in explicit]
        prepare(journal,cid,entries,old,inventory,approvals, tracked_sources=True)
        counts["дубли"] = sum(i.recorded or journal.row(cid,i.number)["status"] in ("matched","verified")
                              for i,a in entries)
    for item, article in entries:
        row = journal.row(cid,item.number)
        if item.recorded or row["status"] in ("verified","matched"):
            continue
        manual = item.number not in held and inventory is None and cid=="barskaya" and item.number=="59"
        approved = row["status"]=="approved" and inventory is not None
        mismatch = item.title and normalize(item.title)!=normalize(article.title)
        if not (approved or manual) or item.hold or mismatch or (manual and article.title!="Снохин долг"):
            counts["проверить"] += 1
            lines.append(f"Сверка № {item.number}: {article.title}")
            if channel["source"]=="queue":
                lines.append("Остальная очередь отложена до сверки этой позиции.")
                break
            continue
        counts["новые"] += 1
        menu = studio.open_menu()
        if manual:
            with journal.db:
                result = journal.db.execute("""UPDATE publications SET status='pending' WHERE channel=? AND number=?
                    AND digest=? AND status IN ('review','approved')""",(cid,item.number,article.digest))
                if result.rowcount!=1:
                    raise ValueError("№ 59 уже зарезервирован")
        else:
            journal.reserve(cid,item.number,article.digest)
        url = studio.create(menu)
        if inventory and url.split("?")[0] in {entry["url"] for entry in inventory}:
            raise ValueError("Дзен открыл материал, который уже был в Студии. Ввод остановлен.")
        with journal.db:
            journal.db.execute("UPDATE publications SET draft_url=? WHERE channel=? AND number=?",
                               (url,cid,item.number))
        finish(journal,studio,cid,item,article,url,False)
        counts["создано"] += 1
        lines.append(f"Сохранён № {item.number} «{article.title}»: {url}")
        print(lines[-1], flush=True)
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
