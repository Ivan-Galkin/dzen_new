# Дочитывания, объём и тексты статей Дзена (для любого канала)

Дополнение к `01_RUNBOOK_ВЫГРУЗКА-ДЗЕН-СТАТЕЙ.md`. Та выгрузка даёт заголовок и просмотры. Этот рецепт даёт по каждой статье: **просмотры, дочитывания, время чтения, полный текст** и замеры текста (знаки, абзацы, доля реплик, длина предложений). Проверен 28.09.2026 на 280 статьях 10 каналов: 243 прочитаны, 37 оказались удалены.

## Что где лежит

- **Дата статьи** зашита в ссылке. `https://dzen.ru/a/aWOAltAcUR5eiV06`: хвост из 16 символов это base64url от 12-байтного ObjectId, **первые 4 байта = Unix-время публикации**.
- **Дочитывания** есть в коде страницы статьи: `"views":323738,"viewsTillEnd":260312`. `viewsTillEnd` это дочитывания; доля дочитавших = viewsTillEnd / views.
- **Время чтения:** `"timeToReadSeconds":526`.
- **Текст:** `"contentState":"..."`, внутри JSON-строка с `draftJsState.blocks` (у каждого блока `type` и `text`; картинки это блоки `atomic`).
- Лайков и комментариев в коде страницы статьи нет (они есть в ленте канала: `socialInfo.likesCount`, `commentCount`).

## Дата из ссылки (Python)

```python
import base64, datetime as dt
def pub_date(url):
    s = url.rstrip('/').split('/a/')[-1].split('?')[0]
    b = base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))
    return dt.datetime.utcfromtimestamp(int.from_bytes(b[:4], 'big'))
```

## Шаги (Claude in Chrome)

1. Открыть любую статью Дзена, чтобы вкладка была на origin `dzen.ru`.
2. Выполнить через `javascript_tool` скрипт ниже, подставив массив ID (хвосты ссылок). Он работает в фоне тремя потоками.
3. Через 1–2 минуты проверить статус: `JSON.stringify({done:Object.keys(__M).length, err:Object.keys(__ERR).length})`.
4. **Выгрузить результат:** вывод `javascript_tool` обрезается примерно на 1–2 тысячах знаков. Поэтому результат кладём на страницу и читаем через `get_page_text`, он отдаёт целиком (проверено на 21 тысяче знаков):
   ```js
   document.body.innerHTML=''; const a=document.createElement('article'); const p=document.createElement('pre');
   p.textContent = Object.entries(__M).map(([id,m])=>[id,m.views,m.vte,m.ttr,m.chars,m.paras,m.dlg,m.aw].join(',')).join('\n');
   a.appendChild(p); document.body.appendChild(a);
   ```
   Потом `get_page_text`. Полные тексты так же: `__T[id]`.
5. Считать агрегаты лучше прямо в браузере и выгружать уже таблицу: это экономит токены.

## Скрипт

```js
window.__IDS = ['aWOAltAcUR5eiV06' /*, ... */];
window.__M = window.__M || {}; window.__T = window.__T || {}; window.__ERR = window.__ERR || {}; window.__INF = {};
window.__parse = h => {
  const g = re => { const m = h.match(re); return m ? m[1] : null; };
  const out = { views: +g(/"views":(\d+),"viewsTillEnd"/), vte: +g(/"viewsTillEnd":(\d+)/), ttr: +g(/"timeToReadSeconds":(\d+)/) };
  const m = h.match(/"contentState":"((?:[^"\\]|\\.)*)"/); if (!m) return null;
  const cs = JSON.parse(JSON.parse('"' + m[1] + '"')); const st = cs.draftJsState || cs;
  out.blocks = (st.blocks || []).map(b => ({ t: b.type, x: b.text || '' }));
  return out;
};
window.__metrics = p => {
  const txt = p.blocks.filter(b => b.x.trim() && !/^atomic/.test(b.t)).map(b => b.x.trim());
  const all = txt.join('\n');
  const sents = all.split(/(?<=[.!?…])\s+|\n/).map(s => s.trim()).filter(s => s.length > 1);
  const wc = sents.map(s => s.split(/\s+/).filter(w => /[А-Яа-яЁё0-9]/.test(w)).length).filter(n => n > 0);
  return { views: p.views, vte: p.vte, ttr: p.ttr, chars: all.length, paras: txt.length,
    dlg: txt.filter(s => /^[—–-]\s?/.test(s)).length,
    aw: +(wc.reduce((a, b) => a + b, 0) / (wc.length || 1)).toFixed(1),
    imgs: p.blocks.filter(b => /^atomic/.test(b.t)).length };
};
window.__worker = async () => {
  while (true) {
    const id = __IDS.find(x => !__M[x] && !__ERR[x] && !__INF[x]); if (!id) break; __INF[id] = 1;
    try {
      const h = await (await fetch('/a/' + id, { credentials: 'include' })).text();
      const p = h.includes('contentState') ? __parse(h) : null;
      if (!p) { __ERR[id] = 'nocontent'; continue; }
      __M[id] = __metrics(p); __T[id] = p.blocks.filter(b => !/^atomic/.test(b.t)).map(b => b.x).join('\n');
    } catch (e) { __ERR[id] = String(e).slice(0, 80); }
  }
};
for (let i = 0; i < 3; i++) __worker(); 'started ' + __IDS.length;
```

## Грабли

- **Не ставить `setTimeout`-паузы в цикле.** Фоновая вкладка Chrome замедляет таймеры до одного срабатывания в минуту: 280 статей шли бы полчаса. Три параллельных потока без пауз прошли 280 статей за 2–3 минуты, капчи не было.
- **`nocontent`** почти всегда значит, что статья удалена (страница «Мы не нашли эту страницу»). Пропускать.
- **Не выводить в ответ `javascript_tool` ссылки с параметрами** (`?...&...`): инструмент блокирует такой вывод целиком. Заменять ссылки на `URL` перед выводом.
- **Страница весит около 1,2 МБ**, 300 статей это 350 МБ трафика браузера. Брать выборку (лучшие, середина, слабые, свежие), а не все статьи канала.
- Долгий `await` дольше 45 секунд внутри одного вызова `javascript_tool` роняет вызов. Ждать отдельными короткими вызовами.
- Браузер может быть залогинен в аккаунт владельца. Читаем только публичные страницы, ничего не нажимаем.

## Как читать цифры

- Доля дочитавших у лидеров сюжетной ниши 0,65–0,95; у хитов обычно ниже, чем у средних статей канала, потому что хит собирает случайную аудиторию.
- Сравнивать статьи внутри одного канала, между каналами только ориентир.
