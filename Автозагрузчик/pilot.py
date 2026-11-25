"""One explicitly selected, already openable draft. Never creates another article."""
import json
import logging
import os
import re
import tempfile
import time
from contextlib import closing
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout, expect, sync_playwright

from main import MODULE, lock, save
from parser import parse
from repository import snapshot
from scanner import scan
from storage import Journal

CHANNEL = "barskaya"
NUMBER = "58"
NAME = "Барская воля"
TITLE = "Вольную отрезали от родника"
LIST = "https://dzen.ru/profile/editor/barskaya_volya/publications"
# Public channel ID visible in the owner's editor address. Draft IDs stay local.
EDITOR = re.compile(r"https://dzen\.ru/profile/editor/id/6ae66f59e7c94415a6b7bed0/[a-f0-9]{24}/edit")
BLOCK = ".public-DraftStyleDefault-block"


def editors(page, url):
    if page.url != url:
        raise ValueError("Адрес изменился. Проверьте канал, вход и адрес черновика.")
    channel = page.get_by_text(NAME, exact=True).filter(visible=True).first
    try:
        expect(channel).to_be_visible(timeout=30000)
    except AssertionError:
        input("Название канала пока не видно. Проверьте вход и загрузку страницы в браузере. Когда увидите «Барская воля», нажмите Enter здесь: ")
        expect(channel).to_be_visible(timeout=30000)
    if page.url != url:
        raise ValueError("После загрузки изменился адрес черновика")
    fields = page.locator('[contenteditable="true"]:visible').filter(has=page.locator(BLOCK))
    expect(fields).to_have_count(2, timeout=30000)
    overlay = page.locator('.ReactModal__Overlay[class*="help-popup"]:visible')
    if overlay.count():
        input("В редакторе открыта подсказка Дзена. Закройте её в браузере и нажмите Enter здесь: ")
        expect(overlay).to_have_count(0, timeout=30000)
    first, second = fields.nth(0), fields.nth(1)
    if first.bounding_box()["y"] >= second.bounding_box()["y"]:
        raise ValueError("Не удалось определить порядок полей")
    return first, second


def paragraphs(field):
    return [s.replace("\xa0", " ").strip() for s in field.locator(BLOCK).all_inner_texts()]


def click_field(page, url, index):
    field = editors(page, url)[index]
    try:
        field.click(timeout=5000)
    except PlaywrightTimeout:
        # A first-visit help popup can appear after the initial editor check.
        editors(page, url)[index].click(timeout=15000)


def fill_and_check(page, url, article, resume, reserve):
    title, body = editors(page, url)
    expected = page.evaluate("""html => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        return [...doc.body.children].map(p => {
            if (p.tagName !== 'P' || p.children.length) throw Error('Формат № 58 изменился');
            return p.textContent.trim();
        });
    }""", article.html())
    if not expected:
        raise ValueError("Пустой рассказ")
    if resume:
        page.reload(wait_until="domcontentloaded")
        title, body = editors(page, url)
    if not resume or not any(paragraphs(title) + paragraphs(body)):
        if any(paragraphs(title) + paragraphs(body)):
            raise ValueError("Выбранный черновик уже содержит текст")
        if not resume:
            reserve()
        click_field(page, url, 0)
        page.keyboard.insert_text(article.title)
        expect(title).to_have_text(article.title)
        _, body = editors(page, url)
        if any(paragraphs(body)):
            raise ValueError("Поле текста уже заполнено")
        click_field(page, url, 1)
        # Use the editor's paste handler; never overwrite its DOM.
        body.evaluate("""(el, data) => {
            if (!el.contains(document.activeElement)) throw Error('Фокус вне текста');
            const clip = new DataTransfer();
            clip.setData('text/plain', data.plain);
            clip.setData('text/html', data.html);
            el.dispatchEvent(new ClipboardEvent('paste', {clipboardData:clip, bubbles:true, cancelable:true}));
        }""", {"html": article.html(), "plain": "\n\n".join(expected)})
        if paragraphs(body) != expected:
            raise ValueError("Редактор не подтвердил вставку всех абзацев")
        expect(page.get_by_text(re.compile(r"^Сохранено(?:\s|$)")).filter(visible=True).first).to_be_visible(timeout=45000)
        page.wait_for_timeout(2500)
    # Only read after a crash. Never paste into an unverified/partial draft again.
    for attempt in range(3):
        page.reload(wait_until="domcontentloaded")
        title, body = editors(page, url)
        if paragraphs(title) == [article.title] and paragraphs(body) == expected:
            return
        if attempt < 2:
            time.sleep(2)
    raise ValueError("После обновления заголовок или абзацы отличаются. Откройте этот же черновик.")


def pilot(state):
    config = state / "config.json"
    channels = json.loads((config if config.exists() else MODULE / "config.example.json")
                          .read_text(encoding="utf-8-sig"))["channels"]
    channel, = [c for c in channels if c["id"] == CHANNEL and c["name"] == NAME]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", channel["profile"]):
        raise ValueError("Некорректный профиль")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        snapshot(state, root, {channel["folder"]})
        item, = [x for x in scan(root, channel) if x.number == NUMBER]
        article = parse(item.path.read_text(encoding="utf-8-sig"))
        relpath = item.path.relative_to(root).as_posix()
    if article.title != TITLE:
        raise ValueError("Название согласованного рассказа изменилось")
    journal = Journal(state / "publications.sqlite")
    with closing(journal.db):
        row = journal.observe(CHANNEL, item, article, relpath)
        if row["status"] in ("matched", "verified"):
            print("Повтор пропущен:", row["draft_url"] or TITLE)
            return
        resume = row["status"] == "pending"
        url = row["draft_url"] if resume else input("Вставьте адрес открытого пустого черновика Барской воли: ").strip()
        if not EDITOR.fullmatch(url or "") or row["digest"] != article.digest:
            raise ValueError("Не совпал адрес канала или версия материала")
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(str(state / "profiles" / channel["profile"]),
                                                           headless=False, locale="ru-RU")
            try:
                page = context.new_page()
                if not resume:
                    page.goto(LIST, wait_until="domcontentloaded")
                    expect(page.get_by_text(NAME, exact=True).filter(visible=True).first).to_be_visible()
                    print("Первичная сверка № 58. Проверьте название и начало текста в опубликованных, "
                          "ожидающих и черновиках. Начало:", article.body.splitlines()[0])
                    if input("Если рассказ уже есть, закройте программу. Если его нет, введите 58: ").strip() != NUMBER:
                        raise ValueError("Первичная сверка отменена")
                page.goto(url, wait_until="domcontentloaded")

                def reserve():
                    with journal.db:
                        result = journal.db.execute("""UPDATE publications SET status='pending',draft_url=?
                            WHERE channel=? AND number=? AND digest=? AND status IN ('review','approved')""",
                            (url, CHANNEL, NUMBER, article.digest))
                        if result.rowcount != 1:
                            raise ValueError("Попытка уже зарегистрирована")

                fill_and_check(page, url, article, resume, reserve)
                page.goto(LIST, wait_until="domcontentloaded")
                expect(page.get_by_text(NAME, exact=True).filter(visible=True).first).to_be_visible()
                tab = page.get_by_text(re.compile(r"^Черновики(?:\s*\d+)?$")).filter(visible=True)
                tab.click()
                expect(page.get_by_text(TITLE, exact=True).filter(visible=True)).to_be_visible(timeout=30000)
                journal.verified(CHANNEL, NUMBER, url)
                save(state / "pilot-result.txt", f"Проверен черновик № 58\n{TITLE}\n{url}")
                print("Черновик № 58 сохранён. Заголовок и все абзацы проверены:", url)
            finally:
                context.close()


if __name__ == "__main__":
    state = Path(os.environ["LOCALAPPDATA"]) / "DzenDraftLoader"
    state.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=state / "technical.log", encoding="utf-8", level=logging.INFO)
    try:
        with lock(state):
            pilot(state)
    except Exception as exc:
        logging.exception("Пилот № 58 остановлен")
        print("Проверка остановлена:", exc)
        raise SystemExit(1)
