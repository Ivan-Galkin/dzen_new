"""Read back text and semantic formatting from the source and a Draft.js editing surface."""
import re
import time

from playwright.sync_api import expect


SIGNATURE = r"""(field, html) => {
 const root = html === null ? field : new DOMParser().parseFromString(html,'text/html').body;
 const selector = html === null ? '.public-DraftStyleDefault-block' :
     'p,h1,h2,h3,h4,h5,h6,li,blockquote,pre,hr,td,th';
 const blocks = [...root.querySelectorAll(selector)].filter(el =>
     !el.querySelector(selector));
 return blocks.map(el => {
    const runs=[];
    function append(text, style) {
        text=text.replace(/\u00a0/g,' ');
        if (!text) return;
        const last=runs[runs.length-1];
        if(last && last[1]===style) last[0]+=text; else runs.push([text,style]);
    }
    function visit(node) {
        if(node.nodeType===3) {
            const marks=new Set();
            for(let e=node.parentElement;e && e!==root;e=e.parentElement){
                if(['B','STRONG'].includes(e.tagName)||['bold','700','800','900'].includes(e.style.fontWeight)) marks.add('b');
                if(['I','EM'].includes(e.tagName)||e.style.fontStyle==='italic') marks.add('i');
                if(e.tagName==='CODE') marks.add('code');
                if(e.tagName==='A') marks.add('href='+e.getAttribute('href'));
            }
            append(node.nodeValue,[...marks].sort().join('|'));
        } else if(node.nodeName==='BR') append('\n','');
        else node.childNodes.forEach(visit);
    }
    visit(el);
    let path=[];
    for(let e=el;e && e!==root;e=e.parentElement){
       if(/^(H[1-6]|UL|OL|LI|BLOCKQUOTE|PRE|TABLE|TR|TD|TH|HR)$/.test(e.tagName)) path.unshift(e.tagName);
    }
    return [path.join('/'),runs];
 });
}"""


def expected_signature(body, article):
    return body.evaluate(SIGNATURE, article.html())


def content_matches(body, expected):
    return body.evaluate(SIGNATURE, None) == expected


def write_rich(page, url, article, name, resume):
    from pilot import editors, paragraphs, click_field
    title, body = editors(page, url, name)
    expected = expected_signature(body, article)
    if not expected:
        raise ValueError("Не удалось определить структуру статьи")
    current = paragraphs(title)
    if not any(paragraphs(body)):
        if any(current) and (not resume or current != [article.title]):
            raise ValueError("Редактор содержит другой заголовок")
        if not any(current):
            click_field(page, url, 0, name)
            page.keyboard.insert_text(article.title)
        expect(title).to_have_text(article.title)
        click_field(page,url,1,name)
        if page.url!=url or any(paragraphs(body)):
            raise ValueError("Страница изменилась перед вставкой")
        # A native paste runs the editor's actual HTML importer. The synthetic
        # paste event was ignored by the live editor during the pilot.
        page.context.grant_permissions(["clipboard-read","clipboard-write"],origin="https://dzen.ru")
        await_clipboard = """async (el,html) => {
            if(!el.contains(document.activeElement)) throw Error('Фокус вне текста');
            const plain=new DOMParser().parseFromString(html,'text/html').body.textContent;
            await navigator.clipboard.write([new ClipboardItem({
              'text/html':new Blob([html],{type:'text/html'}),
              'text/plain':new Blob([plain],{type:'text/plain'})
            })]);
        }"""
        body.evaluate(await_clipboard,article.html())
        page.keyboard.press("Control+v")
        deadline=time.monotonic()+12
        while not content_matches(body,expected):
            if time.monotonic()>=deadline:
                raise ValueError("Редактор изменил текст или форматирование. Черновик оставлен на проверку.")
            page.wait_for_timeout(200)
    elif not resume or current != [article.title] or not content_matches(body,expected):
        raise ValueError("Содержимое черновика требует сверки")
    expect(page.get_by_text(re.compile(r"^Сохранено(?:\s|$)")).filter(visible=True).first).to_be_visible(timeout=45000)
    page.wait_for_timeout(2500)
    page.reload(wait_until="domcontentloaded")
    title,body=editors(page,url,name)
    if paragraphs(title)!=[article.title] or not content_matches(body,expected):
        raise ValueError("После перезагрузки текст или форматирование изменились")
