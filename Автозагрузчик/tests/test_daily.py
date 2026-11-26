import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright

from daily import run_channel
from parser import parse
from rich_text import SIGNATURE
from storage import Journal

ORIGIN = "http://localhost"
CHANNEL_ID = "a"*24
URL = ORIGIN + "/profile/editor/barskaya_volya/publications"

STUDIO = """<strong>Барская воля</strong><button id=plus><svg><path d="M0 0h8"/></svg></button>
<button id=article hidden>Написать статью</button><div id=tabs></div><div id=cards></div>
<script>
const saved=JSON.parse(localStorage.items||'[]');
plus.onclick=()=>article.hidden=false;
article.onclick=()=>{
 const id=(saved.length+1).toString(16).padStart(24,'0');
 saved.push({id,title:'Без названия'});localStorage.items=JSON.stringify(saved);
 location.href='/profile/editor/id/'+'a'.repeat(24)+'/'+id+'/edit';
};
for (const [label,group] of Object.entries({'Опубликованные':[],'Ожидают публикации':[],'Черновики':saved})){
 const b=document.createElement('button'); b.textContent=label+' '+group.length;tabs.append(b);
 b.onclick=()=>{cards.replaceChildren();for(const item of group){const a=document.createElement('a');
 a.href='/profile/editor/id/'+'a'.repeat(24)+'/'+item.id+'/edit';a.textContent=item.title;cards.append(a)}};
}
</script>"""
EDITOR = """<strong>Барская воля</strong><p>Сохранено меньше минуты назад</p>
<div contenteditable=true><div class=public-DraftStyleDefault-block><br></div></div>
<div contenteditable=true><div class=public-DraftStyleDefault-block><br></div></div>
<script>
// Studio may add query parameters after the editor has mounted.
setTimeout(()=>history.replaceState(null,'',location.pathname+'?editor=ready'),150);
const [title,body]=document.querySelectorAll('[contenteditable]');
const saved=JSON.parse(localStorage.items),item=saved.find(i=>location.pathname.includes(i.id+'/edit'));
if(item.titleHtml)title.innerHTML=item.titleHtml;
if(item.bodyHtml)body.innerHTML=item.bodyHtml;
title.oninput=()=>{item.titleHtml=title.innerHTML;item.title=title.innerText.trim();localStorage.items=JSON.stringify(saved)};
body.oninput=()=>{item.bodyHtml=body.innerHTML;localStorage.items=JSON.stringify(saved)};
body.onkeydown=e=>{
 if(e.key!=='Enter')return;
 e.preventDefault();
 const p=document.createElement('div');p.className='public-DraftStyleDefault-block';
 p.append(document.createElement('br'));body.append(p);
 const r=document.createRange();r.setStart(p,0);r.collapse(true);getSelection().removeAllRanges();getSelection().addRange(r);
};
</script>"""


class DailyTest(unittest.TestCase):
    def test_59_next_story_and_repeat(self):
        original = Path(os.environ.get("DZEN_TEST_SOURCE", Path(__file__).resolve().parents[2]))
        filename = "Рассказ-59_ГОТОВО-К-ВСТАВКЕ.md"
        raw = (original/"Барская воля"/filename).read_text(encoding="utf-8-sig")
        with tempfile.TemporaryDirectory() as directory, sync_playwright() as pw:
            root = Path(directory)
            base = root/"Барская воля"
            base.mkdir()
            
            (base/filename.replace("59","57")).write_text("Архив\n\nСтарый текст",encoding="utf-8")
            journal=Journal(root/"journal.sqlite")
            channel=dict(id="barskaya", name="Барская воля", folder="Барская воля", source="stories",
                         studio_url="https://dzen.ru/profile/editor/barskaya_volya", editor_channel_id=CHANNEL_ID)
            browser=pw.chromium.launch()
            ctx=browser.new_context()
            def route(r):
                r.fulfill(content_type="text/html; charset=utf-8",body=EDITOR if r.request.url.split("?")[0].endswith("/edit") else STUDIO)
            ctx.route("**/*",route)
            from studio import Studio
            class OfflineStudio(Studio):
                def __init__(self,*args):
                    super().__init__(*args)
                    self.list_url=URL
                def open_menu(self):
                    if not self.icon_path.exists():
                        # Simulate the owner's single calibration click after the listener exists.
                        self.page.add_init_script("setInterval(()=>{if(window.dzenCreateIcon===null && document.querySelector('#article[hidden]'))plus.click()},80)")
                    return super().open_menu()
            try:
                with patch("daily.Studio",OfflineStudio), patch("studio.EDIT",re.compile(ORIGIN+r"/profile/editor/id/([a-f0-9]{24})/([a-f0-9]{24})/edit")):
                    def run():
                        return run_channel(root,root,journal,channel,ctx,[])["создано"]
                    self.assertEqual(run(),0)
                    (base/filename).write_text(raw,encoding="utf-8")
                    self.assertEqual(run(),1)
                    self.assertEqual(run(),0)
                    self.assertEqual(journal.row("barskaya","57"),None)
                    self.assertEqual(journal.row("barskaya","59")["status"],"verified")
                    stored=ctx.pages[-1].evaluate("JSON.parse(localStorage.items)")
                    source=parse(raw)
                    actual=ctx.pages[-1].evaluate("html=>new DOMParser().parseFromString(html,'text/html').body.textContent",stored[0]["bodyHtml"])
                    for image in source.images:
                        for line in image["prompt"].splitlines():
                            self.assertIn(line,actual)
                        if image["after"]!="После заголовка":
                            self.assertLess(actual.index(image["after"]),actual.index(image["prompt"].splitlines()[0]))
                    (base/filename.replace("59","60")).write_text("Другой заголовок\n\nНовый абзац.",encoding="utf-8")
                    # Emulate an earlier attempt that stopped before capturing the URL.
                    with journal.db:
                        journal.db.execute("INSERT INTO publications SELECT channel,'60',kind,path,title,digest,'pending',NULL,NULL,NULL FROM publications WHERE number='59'")
                    self.assertEqual(run(),1)
                    self.assertEqual(run(),0)
                    self.assertEqual(len(ctx.pages[-1].evaluate("JSON.parse(localStorage.items)")),2)
            finally:
                journal.db.close()
                browser.close()

    def test_rich_signature_detects_format_loss(self):
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            page=browser.new_page()
            page.set_content("<div id='body'><h2><div class='public-DraftStyleDefault-block'><em>Тема</em></div></h2></div>")
            body=page.locator("#body")
            self.assertEqual(body.evaluate(SIGNATURE,None),body.evaluate(SIGNATURE,"<h2><em>Тема</em></h2>"))
            self.assertNotEqual(body.evaluate(SIGNATURE,None),body.evaluate(SIGNATURE,"<p>Тема</p>"))
            browser.close()
