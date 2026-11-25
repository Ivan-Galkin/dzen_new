"""Visible Studio navigation. Learn the unlabelled + button from one owner click."""
import json
import re
import time
from urllib.parse import urlsplit

from playwright.sync_api import expect

from pilot import channel_label, draft_address, editors, fill_and_check
from rich_text import write_rich

TABS = {"published": "Опубликованные", "scheduled": "Ожидают публикации", "draft": "Черновики"}
EDIT = re.compile(r"https://dzen\.ru/profile/editor/id/([a-f0-9]{24})/([a-f0-9]{24})/edit")
CARD = re.compile(r"(?:/a/[^/]+|/b/[^/]+|/media/[^/]+/[^/]+|/profile/editor/id/[a-f0-9]{24}/[a-f0-9]{24}/edit)/?$")

# Record only the toolbar icon. No text input, session data or other clicks.
ICON = """button => {
    if (!button || (button.innerText || '').trim()) return null;
    const svg = button.querySelector('svg');
    return svg ? svg.outerHTML : null;
}"""


class Studio:
    def __init__(self, context, channel, state):
        self.context = context
        self.page = context.new_page()
        self.name = channel.get("studio_name", channel["name"])
        base = channel["studio_url"].rstrip("/").removesuffix("/publications")
        if not re.fullmatch(r"https://dzen\.ru/profile/editor/(?:id/)?[\w.-]+", base):
            raise ValueError("Укажите адрес главной страницы Студии канала")
        self.list_url = base + "/publications"
        self.icon_path = state / "create-button.json"
        self.editor_id = channel.get("editor_channel_id")
        self.state = state

    def require_list(self):
        if self.page.url.split("?")[0].rstrip("/") != self.list_url:
            raise ValueError("Дзен переключил канал или запросил вход")
        expect(self.page.get_by_text(channel_label(self.name)).filter(visible=True).first).to_be_visible(timeout=30000)

    def listing(self):
        self.page.goto(self.list_url, wait_until="domcontentloaded", timeout=60000)
        self.require_list()

    def tab(self, state):
        name = TABS[state]
        entry = self.page.get_by_text(re.compile("^" + name + r"\s*\d[\d\s]*$")).filter(visible=True).first
        expect(entry).to_be_visible(timeout=15000)
        count = int("".join(re.findall(r"\d", entry.inner_text())))
        entry.click()
        self.require_list()
        return count

    def inventory(self):
        self.listing()
        listings = []
        for status in TABS:
            count = self.tab(status)
            records = {}
            previous = set()
            stalled = 0
            self.page.evaluate("scrollTo(0,0)")
            # Card links must account for the entire displayed tab count. Never
            # use a partially loaded list as proof an article is absent.
            for _ in range(200 if count else 0):
                self.page.wait_for_timeout(450)
                anchors = self.page.locator("a[href]:visible").evaluate_all(
                    "(nodes) => nodes.map(a=>[a.href,a.innerText.trim()])")
                for url, text in anchors:
                    link = urlsplit(url)
                    origin = urlsplit(self.list_url)
                    if (link.scheme, link.netloc) != (origin.scheme, origin.netloc) or not CARD.fullmatch(link.path) or not text:
                        continue
                    key = link.path.rstrip("/")
                    records[key] = dict(id=key, url=f"{origin.scheme}://{origin.netloc}{key}", title=text.splitlines()[0], status=status)
                if len(records) == count:
                    break
                stalled = stalled+1 if set(records) == previous else 0
                previous = set(records)
                if stalled >= 8 or len(records) > count:
                    break
                self.page.mouse.wheel(0, 780)
            if len(records) != count:
                raise ValueError(f"Вкладка «{TABS[status]}»: удалось сверить {len(records)} из {count}")
            listings.extend(records.values())
        if len({r["id"] for r in listings}) != len(listings):
            raise ValueError("Содержимое вкладок изменилось во время сверки")
        return listings

    def open_menu(self):
        self.listing()
        menu = self.page.get_by_text("Написать статью", exact=True).filter(visible=True)
        labelled = self.page.get_by_role("button", name="+", exact=True)
        if labelled.count() == 1:
            labelled.click()
            expect(menu).to_be_visible(timeout=10000)
            return menu
        signature = json.loads(self.icon_path.read_text(encoding="utf-8")) if self.icon_path.exists() else None
        buttons = self.page.locator('button:visible,[role="button"]:visible')
        if signature:
            matches = buttons.evaluate_all("(bs,s)=>bs.map((b,i)=>("+ICON+")(b)===s?i:-1).filter(i=>i>=0)",signature)
            if len(matches)==1:
                buttons.nth(matches[0]).click()
                expect(menu).to_be_visible(timeout=10000)
                return menu
        self.page.evaluate("""() => {
          window.dzenCreateIcon = null;
          document.addEventListener('click', e => {
            window.dzenCreateIcon = ("""+ICON+""")(e.target.closest('button,[role=button]') || e.target.closest('svg')?.parentElement);
          }, {capture:true, once:true});
        }""")
        self.page.bring_to_front()
        print(f"Настройка кнопки в канале «{self.name}»: один раз нажмите + вверху. Программе нужен только открытый список действий.", flush=True)
        expect(menu).to_be_visible(timeout=180000)
        signature = self.page.evaluate("window.dzenCreateIcon")
        if signature:
            self.icon_path.write_text(json.dumps(signature), encoding="utf-8")
        return menu

    def create(self, menu):
        self.require_list()
        before = {p: p.url for p in self.context.pages}
        menu.click()
        until = time.monotonic()+45
        while time.monotonic()<until:
            found = [p for p in self.context.pages if before.get(p)!=p.url and EDIT.fullmatch(draft_address(p.url))]
            if len(found)==1:
                self.page = found[0]
                url = self.page.url
                self.check_editor(url)
                return url
            if len(found)>1:
                raise ValueError("Открылось несколько редакторов")
            self.page.wait_for_timeout(200)
        raise ValueError("Не получен адрес нового черновика")

    def check_editor(self, url):
        match = EDIT.fullmatch(draft_address(url))
        if not match or (self.editor_id and match[1]!=self.editor_id):
            raise ValueError("Адрес редактора не соответствует каналу")
        editors(self.page, url, self.name)

    def verify_list(self, article):
        self.listing()
        self.tab("draft")
        expect(self.page.get_by_text(article.title, exact=True).filter(visible=True)).to_have_count(1, timeout=30000)

    def write(self, url, article, resume):
        self.check_editor(url)
        plain = self.page.evaluate("""html => {
            const doc = new DOMParser().parseFromString(html,'text/html');
            return [...doc.body.children].every(p=>p.tagName==='P' && !p.children.length);
        }""", article.html())
        if plain:
            fill_and_check(self.page, url, article, resume, lambda: None, self.name)
        else:
            write_rich(self.page, url, article, self.name, resume)
        self.verify_list(article)
