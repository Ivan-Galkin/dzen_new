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


def draft_address(value):
    return value.strip().split("#", 1)[0].split("?", 1)[0].rstrip("/")


def select_draft(context, page):
    prompt = "Откройте нужный черновик и вставьте сюда его адрес из строки браузера (или Enter для поиска вкладки, 0 для выхода): "
    while True:
        answer = input(prompt).strip()
        if answer == "0":
            raise ValueError("Остановлено владельцем")
        target = draft_address(answer)
        if answer and not EDITOR.fullmatch(target):
            print("Нужна ссылка на редактор статьи «Барской воли» с окончанием /edit.")
            continue
        deadline = time.monotonic() + (0 if target else 5)
        while True:
            matches = [p for p in context.pages if EDITOR.fullmatch(draft_address(p.url))
                       and (not target or draft_address(p.url) == target)]
            if matches and (target or len(matches) == 1):
                return matches[-1]
            if time.monotonic() >= deadline:
                break
            page.wait_for_timeout(250)
        if target:
            page.goto(target, wait_until="domcontentloaded", timeout=60000)
            if draft_address(page.url) != target:
                raise ValueError("При открытии подтверждённого адреса Дзен перенаправил вкладку")
            return page
        print(f"Подходящих вкладок: {len(matches)}. Скопируйте ссылку открытого черновика и вставьте в консоль.")


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
    current_title = paragraphs(title)
    empty_body = not any(paragraphs(body))
    if not resume or (empty_body and (not any(current_title) or current_title == [article.title])):
        if not empty_body or (any(current_title) and not resume):
            raise ValueError("Выбранный черновик уже содержит текст")
        if not resume:
            reserve()
        if not any(current_title):
            click_field(page, url, 0)
            page.keyboard.insert_text(article.title)
        expect(title).to_have_text(article.title)
        _, body = editors(page, url)
        if any(paragraphs(body)):
            raise ValueError("Поле текста уже заполнено")
        click_field(page, url, 1)
        # This pilot accepts plain paragraphs only (validated above). Use native
        # editor input and verify each new block before advancing to the next.
        for index, paragraph in enumerate(expected):
            if page.url != url or not body.evaluate("el => el.contains(document.activeElement)"):
                raise ValueError("Редактор потерял фокус. Ввод остановлен.")
            if index:
                page.keyboard.press("Enter")
                expect(body.locator(BLOCK)).to_have_count(index + 1, timeout=10000)
            page.keyboard.insert_text(paragraph)
            expect(body.locator(BLOCK).nth(index)).to_have_text(paragraph, timeout=10000)
        if paragraphs(body) != expected:
            raise ValueError("Текст отличается от исходника после ввода")
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
        if not EDITOR.fullmatch(draft_address(url or "")) or row["digest"] != article.digest:
            raise ValueError("Не совпал адрес канала или версия материала")
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(str(state / "profiles" / channel["profile"]),
                                                           headless=False, locale="ru-RU")
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.bring_to_front()
                response = page.goto(LIST, wait_until="domcontentloaded", timeout=60000)
                if response and response.status >= 400:
                    raise ValueError(f"Страница публикаций вернула HTTP {response.status}")
                expect(page.get_by_text(NAME, exact=True).filter(visible=True).first).to_be_visible(timeout=60000)
                if not resume:
                    print("Первичная сверка № 58. Проверьте название и начало текста в опубликованных, "
                          "ожидающих и черновиках. Начало:", article.body.splitlines()[0])
                    if input("Если рассказ уже есть, закройте программу. Если его нет, введите 58: ").strip() != NUMBER:
                        raise ValueError("Первичная сверка отменена")
                    page.goto(url, wait_until="domcontentloaded")
                else:
                    page.get_by_text(re.compile(r"^Черновики(?:\s*\d+)?$")).filter(visible=True).click()
                    print("Открыт список черновиков Барской воли. Откройте из списка черновик для № 58.")
                    print("Если список пуст, проверьте опубликованные и ожидающие материалы. Если № 58 нигде нет,"
                          " откройте новый пустой редактор через «+» → «Написать статью». Для выхода введите 0.")
                    page = select_draft(context, page)
                    page.bring_to_front()
                    if draft_address(page.url) != draft_address(url):
                        title_field, body_field = editors(page, page.url)
                        if any(paragraphs(title_field) + paragraphs(body_field)):
                            raise ValueError("Другой черновик уже содержит текст")
                        print("Открыт пустой черновик с другим адресом. Проверьте по спискам канала,"
                              " что рассказ № 58 ещё не загружен.")
                        if input("Чтобы использовать именно этот пустой черновик для № 58, введите 58: ").strip() != NUMBER:
                            raise ValueError("Замена адреса отменена")
                        with journal.db:
                            journal.db.execute("UPDATE publications SET draft_url=? WHERE channel=? AND number=? "
                                               "AND status='pending' AND draft_url=?", (page.url, CHANNEL, NUMBER, url))
                    url = page.url

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
            except Exception as exc:
                logging.exception("Ошибка работы с редактором № 58")
                print("Остановлено:", exc)
                input("Браузер оставлен открытым. Нажмите Enter здесь, когда будете готовы закрыть его: ")
                raise
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
