import unittest
from unittest.mock import Mock

from playwright.sync_api import sync_playwright

from parser import parse
from pilot import fill_and_check


class PilotTest(unittest.TestCase):
    def test_reload_and_recovery_in_offline_browser(self):
        html = """<strong>Барская воля</strong><p>Сохранено меньше минуты назад</p>
        <div contenteditable=true><div class=public-DraftStyleDefault-block><br></div></div>
        <div contenteditable=true><div class=public-DraftStyleDefault-block><br></div></div>
        <script>
        const [title,body]=document.querySelectorAll('[contenteditable]');
        title.oninput=()=>sessionStorage.title=title.innerHTML;
        body.onpaste=e=>{
          e.preventDefault();
          const doc=new DOMParser().parseFromString(e.clipboardData.getData('text/html'),'text/html');
          body.replaceChildren(...[...doc.body.children].map(p=>{
            p.className='public-DraftStyleDefault-block';return p;
          }));
          sessionStorage.body=body.innerHTML;
        };
        if(sessionStorage.title)title.innerHTML=sessionStorage.title;
        if(sessionStorage.body)body.innerHTML=sessionStorage.body;
        </script>"""
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            url = "http://localhost/fixture"
            page.route("**/*", lambda route: route.fulfill(content_type="text/html; charset=utf-8", body=html))
            page.goto(url)
            article = parse("Заголовок\n\nПервый абзац.\n\n— Диалог.")
            reserve = Mock()
            fill_and_check(page, url, article, False, reserve)
            fill_and_check(page, url, article, True, reserve)
            page.evaluate("sessionStorage.clear()")
            fill_and_check(page, url, article, True, reserve)
            with self.assertRaisesRegex(ValueError, "уже содержит"):
                fill_and_check(page, url, article, False, reserve)
            reserve.assert_called_once()
            browser.close()
