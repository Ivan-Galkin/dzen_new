import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from playwright.sync_api import sync_playwright

from parser import parse
from pilot import fill_and_check, select_draft


class PilotTest(unittest.TestCase):
    def test_pasted_address_selects_among_two_editors(self):
        base = "https://dzen.ru/profile/editor/id/6ae66f59e7c94415a6b7bed0/"
        first = Mock(url=base + "a"*24 + "/edit")
        other = Mock(url=base + "b"*24 + "/edit?source=list")
        context = Mock(pages=[first, other])
        with patch("builtins.input", side_effect=["", other.url]), patch("pilot.time.monotonic", side_effect=[0,6,7]):
            self.assertIs(select_draft(context, first), other)
        first.goto.assert_not_called()

    def test_reload_and_recovery_in_offline_browser(self):
        html = """<strong>Барская воля</strong><p>Сохранено меньше минуты назад</p>
        <div contenteditable=true><div class=public-DraftStyleDefault-block><br></div></div>
        <div contenteditable=true><div class=public-DraftStyleDefault-block><br></div></div>
        <script>
        const [title,body]=document.querySelectorAll('[contenteditable]');
        title.oninput=()=>sessionStorage.title=title.innerHTML;
        body.oninput=()=>sessionStorage.body=body.innerHTML;
        body.onkeydown=e=>{
          if(e.key!=='Enter')return;
          e.preventDefault();
          const p=document.createElement('div');
          p.className='public-DraftStyleDefault-block';
          p.append(document.createElement('br'));body.append(p);
          const range=document.createRange();range.setStart(p,0);range.collapse(true);
          const sel=getSelection();sel.removeAllRanges();sel.addRange(range);
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
            root = Path(os.environ.get("DZEN_TEST_SOURCE", Path(__file__).resolve().parents[2]))
            story = root / "Барская воля" / "Рассказ-58_ГОТОВО-К-ВСТАВКЕ.md"
            article = parse(story.read_text(encoding="utf-8-sig"))
            reserve = Mock()
            fill_and_check(page, url, article, False, reserve)
            fill_and_check(page, url, article, True, reserve)
            page.evaluate("sessionStorage.removeItem('body')")
            fill_and_check(page, url, article, True, reserve)
            page.evaluate("sessionStorage.clear()")
            fill_and_check(page, url, article, True, reserve)
            with self.assertRaisesRegex(ValueError, "уже содержит"):
                fill_and_check(page, url, article, False, reserve)
            reserve.assert_called_once()
            browser.close()
