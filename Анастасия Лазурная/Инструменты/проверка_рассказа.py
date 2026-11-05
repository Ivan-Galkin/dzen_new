# Проверка рассказа канала «Анастасия Лазурная» по числам из ИНСТРУКЦИЯ.md (объём и лицо канала) и Формы_рассказов.md (05.11.2026, на основе проверки «Барской воли»).
# Запуск: python3 проверка_рассказа.py Рассказ-05_ГОТОВО-К-ВСТАВКЕ.md --форма повесть --лицо я
# Лицо: я (по умолчанию), я-свидетель, она.
import re, sys

if len(sys.argv) < 2:
    print('Укажите файл рассказа'); sys.exit(1)
path = sys.argv[1]
chapter = '--глава' in sys.argv

# Формы рассказа (с 30.10.2026): правила в Формы_рассказов.md. Без --форма проверяется классический рассказ.
# Запуск: python3 проверка_рассказа.py Рассказ-50_ГОТОВО-К-ВСТАВКЕ.md --форма повесть [--глава]
FORMS = {
    'рассказ':   dict(name='классический рассказ', lo=14000, hi=17000, paras=(95, 150),  dia=(0.30, 0.55), parts=(2, 3)),
    'повесть':   dict(name='повесть в одной статье', lo=20000, hi=25000, paras=(130, 210), dia=(0.30, 0.55), parts=(3, 3)),
    'исповедь':  dict(name='исповедь, первое лицо', lo=20000, hi=25000, paras=(130, 210), dia=(0.25, 0.55), parts=(3, 3)),
    'линии':     dict(name='две линии',            lo=20000, hi=26000, paras=(130, 220), dia=(0.30, 0.55), parts=(3, 5)),
    'перебивка': dict(name='тогда и сейчас: перебивка', lo=20000, hi=26000, paras=(130, 220), dia=(0.30, 0.55), parts=(3, 7)),
    'хроника':   dict(name='тогда и сейчас: хроника', lo=16000, hi=22000, paras=(100, 180), dia=(0.15, 0.55), parts=(3, 6)),
    'ошиблась':  dict(name='ошиблась в человеке (тест по команде владельца)', lo=16000, hi=24000, paras=(100, 200), dia=(0.30, 0.55), parts=(3, 3)),
}
form = 'рассказ'
for _i, _a in enumerate(sys.argv):
    if _a.startswith('--форма='):
        form = _a.split('=', 1)[1]
    elif _a == '--форма' and _i + 1 < len(sys.argv):
        form = sys.argv[_i + 1]
form = form.strip().lower()
face = 'я'
for _i, _a in enumerate(sys.argv):
    if _a.startswith('--лицо='):
        face = _a.split('=', 1)[1]
    elif _a == '--лицо' and _i + 1 < len(sys.argv):
        face = sys.argv[_i + 1]
face = face.strip().lower()
if face not in ('я', 'я-свидетель', 'она'):
    print('Неизвестное лицо:', face, '| есть: я, я-свидетель, она'); sys.exit(1)
if form == 'исповедь' and face == 'она':
    print('Исповедь всегда от первого лица: --лицо я'); sys.exit(1)
if form not in FORMS:
    print('Неизвестная форма:', form, '| есть:', ', '.join(FORMS)); sys.exit(1)
P = FORMS[form]
print(f'Форма: {form} ({P["name"]}); лицо: {face}' + ('; глава' if chapter else ''))
t = open(path, encoding='utf-8').read()

t2 = re.sub(r'\*\*\[.*?\]\*\*', '', t)
t2 = re.sub(r'```.*?```', '', t2, flags=re.S)
t2 = re.sub(r'Подпись: Изображение создано ИИ', '', t2)
lines = [l.strip() for l in t2.split('\n') if l.strip()]
service = ('Спасибо, что дочитали', 'Продолжение истории ниже', 'Начало истории здесь')
body = [l for l in lines[1:] if not l.lstrip('*').startswith(service)]
paras = [l for l in body if l not in ('***', 'ЭПИЛОГ')]
text = '\n'.join(paras)

sents = []
for p in paras:
    for x in re.split(r'(?<=[.!?…])\s+(?=[«А-ЯЁ]|— [А-ЯЁ])', p):
        x = x.strip('— ').strip()
        if x:
            sents.append(x)
wc = [len(re.findall(r'[А-Яа-яЁёA-Za-z0-9-]+', s)) for s in sents]

problems = []
def check(ok, label, value, norm):
    mark = 'OK        ' if ok else 'ИСПРАВИТЬ '
    print(f'{mark}{label}: {value} (норма {norm})')
    if not ok:
        problems.append(label)

n = len(text)
lo, hi = (12000, 16000) if chapter else (P['lo'], P['hi'])
pl, ph = (80, 140) if chapter else P['paras']
check(lo <= n <= hi, 'Знаков', n, f'{lo}–{hi}')
check(pl <= len(paras) <= ph, 'Абзацев', len(paras), f'{pl}–{ph}')
dia = [p for p in paras if p.startswith('—')]
share = len(dia) / len(paras) if paras else 0
dl, dh = P['dia']
check(dl <= share <= dh, 'Абзацев-реплик', f'{share:.0%}', f'{dl*100:.0f}–{dh*100:.0f}%')
_FIRST = {'я', 'мне', 'меня', 'мной', 'мною', 'мой', 'моя', 'моё', 'мое', 'мои', 'мою', 'моего', 'моей', 'моих', 'моим', 'моими', 'моему', 'моём', 'моем'}
_nar = [p for p in paras if not p.startswith('—') and not p.startswith(('*', '_'))]
_w = re.findall(r'[а-яё]+', ' '.join(_nar).lower())
fp = sum(1 for x in _w if x in _FIRST) * 100 / max(1, len(_w))
if face in ('я', 'я-свидетель'):
    check(fp >= 1.5, '«Я» рассказчицы в повествовании', f'{fp:.1f} на 100 слов', 'не меньше 1,5: рассказ от первого лица')
else:
    check(fp <= 1.0, '«Я» в повествовании', f'{fp:.1f} на 100 слов', 'третье лицо: «я» только в репликах и сообщениях')
_parts = sum(1 for l in lines if l == '***')
_pl, _ph = P['parts']
check(_pl <= _parts <= _ph, 'Строк ***', _parts, f'{_pl}–{_ph}: четыре части в рассказе от 15 тысяч')
avg = sum(wc) / len(wc) if wc else 0
check(6.5 <= avg <= 9.5, 'Слов в предложении', round(avg, 2), '7–9, допустимо 6,5–9,5 (у Градова около 8)')
longs = sum(1 for w in wc if w >= 11) / len(wc) if wc else 0
check(longs <= 0.30, 'Длинных предложений (11+ слов)', f'{longs:.0%}', 'не больше 30%')

runs = []
i = 0
while i < len(wc):
    if wc[i] <= 5:
        j = i
        while j < len(wc) and wc[j] <= 5: j += 1
        if j - i >= 4: runs.append(f'коротких подряд {j-i}: ' + ' | '.join(sents[i:j]))
        i = j
    elif wc[i] >= 11:
        j = i
        while j < len(wc) and wc[j] >= 11: j += 1
        if j - i >= 3: runs.append(f'длинных подряд {j-i}: ' + ' | '.join(s[:50] for s in sents[i:j]))
        i = j
    else:
        i += 1
check(not runs, 'Серии предложений', 'нет' if not runs else len(runs), 'не больше 3 коротких и 2 длинных подряд')
for r in runs: print('    ', r)

dash = [p[:80] for p in paras if not p.startswith('—') and '—' in p]
check(not dash, 'Тире в авторском тексте', 'нет' if not dash else len(dash), 'только в репликах')
for d in dash: print('    ', d)
digits = re.findall(r'\d+', text)
check(not digits, 'Цифры в тексте', 'нет' if not digits else digits, 'числа словами, цифры только в документах')
check('"' not in text, 'Прямые кавычки', 'нет' if '"' not in text else 'есть', 'только «ёлочки»')

stamps = ['однако', 'является', 'данный', 'стоит отметить', 'ком в горле', 'время словно остановилось',
          'сердце', 'слеза', 'слёзы', 'повисла тишина', 'мир рухнул', 'внутри всё оборвалось', 'с замиранием',
          'сползла по стене', 'токсичн', 'абьюз', 'газлайт', 'личные границы', 'ресурс', 'кринж']
found = [w for w in stamps if w in text.lower()]
if re.search(r'(?<![а-яё])затем(?![а-яё])', text.lower()): found.append('затем')
check(not found, 'Штампы', 'нет' if not found else ', '.join(found), 'заменить действием или деталью')

_BRANDS = ['сбербанк', 'тинькоф', 'т-банк', 'втб', 'альфа-банк', 'альфабанк', 'озон', 'ozon', 'вайлдберри', 'wildberries', 'авито', 'яндекс', 'ватсап', 'whatsapp', 'телеграм', 'telegram', 'вконтакте', 'пятёрочк', 'пятерочк', 'перекрёст', 'перекрест', 'ашан', 'макдоналдс', 'вкусно и точка', 'мвидео', 'эльдорадо', 'айфон', 'iphone', 'самсунг', 'тойот', 'хендай', 'хёндай']
_tl = text.lower()
_br = sorted({b for b in _BRANDS if re.search(r'(?<![а-яёa-z])' + re.escape(b), _tl)})
check(not _br, 'Бренды', 'нет' if not _br else ', '.join(_br), 'без названий банков, магазинов, сервисов, марок: «приложение банка», «маркетплейс», «мессенджер» (Госуслуги, МФЦ, Росреестр можно)')

need = ['Подпись: Изображение создано ИИ', 'wide 16:9 aspect ratio']
first_chapter = chapter and '. Глава 2' not in t.split('\n')[0]
if first_chapter:
    need.append('Продолжение истории ниже')
else:
    need.append('Спасибо, что дочитали. Если история тронула, поставьте лайк и подпишитесь на канал.')
plain = t.replace('**', '')
miss = [x[:40] for x in need if x not in plain]
check(not miss, 'Обязательные строки', 'все на месте' if not miss else miss, 'подписи к картинкам; строка призыва, а в главе 1 строка «Продолжение истории ниже»')
check(t.count('```') == 6, 'Промтов к картинкам', t.count('```') // 2, '3')


# Против шаблона (с 26.10.2026): строка ЭПИЛОГ (с 31.10.2026 не чаще одного из трёх), зачин «Было это…», финал-реликвия в сравнении с тремя прошлыми рассказами папки
import os, glob
def _num(fn):
    m = re.search(r'Рассказ-(\d+)(?:-(\d))?_', os.path.basename(fn))
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None
def _paras(txt):
    x = re.sub(r'\*\*\[.*?\]\*\*', '', txt)
    x = re.sub(r'```.*?```', '', x, flags=re.S)
    x = x.replace('Подпись: Изображение создано ИИ', '').replace('**', '')
    ls = [l.strip() for l in x.split('\n') if l.strip()]
    return [l for l in ls[1:] if not l.startswith(service) and l not in ('***', 'ЭПИЛОГ')]
_RELIC = re.compile(r'до сих пор|так и (висит|висят|лежит|лежат|стоит|хранится)|хранит|хранится|берегла|бережёт|висит у|висят у|лежит у|лежат у|под стеклом|в рамке', re.I)
def _bylo(p): return bool(re.search(r'(^|[\s«])Было это', ' '.join(p[:8])))
def _relic(p): return bool(p) and bool(_RELIC.search(p[-1]))
cur = _num(path)
_epi = lambda txt: 'ЭПИЛОГ' in [l.strip().strip('*').strip() for l in txt.split('\n')]
if cur:
    folder = os.path.dirname(os.path.abspath(path))
    files = {}
    for f in glob.glob(os.path.join(folder, 'Рассказ-*_ГОТОВО-К-ВСТАВКЕ.md')):
        n = _num(f)
        if n and n[0] < cur[0]:
            files.setdefault(n[0], {})[n[1]] = f
    prev = sorted(files)[-3:]
    def _get(num, kind):
        d = files[num]
        f = d.get(0) or (d.get(1) if kind == 'zachin' else d.get(2))
        return _paras(open(f, encoding='utf-8').read()) if f else None
    mine = _paras(t)
    if cur[1] != 2:
        prev2 = [_get(n, 'zachin') for n in prev[-2:]]
        bad = _bylo(mine) and any(p and _bylo(p) for p in prev2)
        check(not bad, 'Зачин «Было это…»', 'повтор' if bad else 'нет повтора', 'не чаще одного рассказа из трёх')
    if cur[1] != 1:  # строка «ЭПИЛОГ» (с 31.10.2026): можно, но не чаще одного рассказа из трёх
        prevE = []
        for n in prev[-2:]:
            f = files[n].get(0) or files[n].get(2)
            if f: prevE.append(open(f, encoding='utf-8').read())
        bad = _epi(t) and any(_epi(x) for x in prevE)
        check(not bad, 'Строка «ЭПИЛОГ»', 'повтор' if bad else ('есть' if _epi(t) else 'нет'), 'можно, но не чаще одного рассказа из трёх (с 31.10.2026)')
    if cur[1] != 1:
        prev3 = [_get(n, 'final') for n in prev]
        bad = _relic(mine) and any(p and _relic(p) for p in prev3)
        check(not bad, 'Финал-вещь', 'повтор' if bad else 'нет повтора', 'вещь-реликвия в последнем абзаце не чаще одного рассказа из четырёх')

# Л14 (с 30.10.2026): второстепенный герой мелькнул и вернулся через 5 000+ знаков. Скрипт только подсказывает,
# где проверить: если в той же фразе не напомнено, кто он, и напоминание уместно, добавить одну-две приметы.
_GAP = 5000
_END = ('ыми', 'ими', 'ами', 'ями', 'ому', 'ему', 'ого', 'его', 'ой', 'ей', 'ым', 'им', 'ом', 'ем', 'ам', 'ям', 'ах', 'ях', 'ых', 'их',
        'у', 'ю', 'а', 'я', 'ы', 'и', 'е')
def _stem(w):
    w = w.lower().replace('ё', 'е')
    for e in _END:
        if w.endswith(e) and len(w) - len(e) >= 2:
            w = w[:-len(e)]; break
    return w.rstrip('ьй')
_NOTNAME = ('бог', 'господ', 'христ', 'богородиц', 'пасх', 'рождеств', 'крещен', 'троиц', 'покров', 'маслен', 'велик', 'пост', 'светл', 'красн', 'горк',
            'спас', 'восьм', 'петров', 'ильин', 'никол', 'благовещ', 'вознесен', 'успен', 'новый', 'нового', 'новом', 'первомай', 'октябр', 'побед',
            'ключ', 'заречь', 'ольхов', 'ольшанк', 'покровск', 'кочетовк', 'осиновк', 'сокольц', 'ивиц', 'гусев', 'тепл', 'хомутовк', 'москв', 'ленинград', 'росси', 'волг', 'сибир', 'урал', 'кавказ', 'крым', 'петербург',
            'киев', 'казан', 'саратов', 'пенз', 'берлин', 'германи', 'ведомост', 'губернск', 'правд', 'известия', 'советск', 'союз', 'ссср', 'родин')
_ROLE = re.compile(r'(майор|дяд|тет|нян|предводител|председател|судь|старост|свекров|свекр|золовк|девер|невестк|снох|сосед|бригадир|учител|фельдшер|доктор|врач|'
                   r'батюшк|поп|барин|барын|барышн|купец|купц|купчих|приказчик|исправник|управляющ|инспектор|директор|парторг|агроном|почтальон|кум|крестн|'
                   r'внук|внучк|брат|сестр|отец|отц|мать|матер|муж|жен|вдов|шофер|тракторист|кладовщик|счетовод|продавщиц|завмаг|лесник|пастух|кузнец|мельник|конюх|'
                   r'повитух|сын|доч|зят|тест|тещ|племянни|падчериц|пасын|мачех|отчим|мельничих|стар|помещиц|полковниц|генеральш|дворнич|портних|почтмейстер|ротмистр|штабс|кухарк|горничн|ключниц|экономк|гувернантк|сват|кучер|'
                   r'бабк|бабушк|дед|товарищ|друг|подруг|заседател|офицер|полковник|генерал|капитан|поручик|денщик|солдат|унтер|писар|урядник|лавочник|'
                   r'мастер|начальник|комендант|вахтер|дворник|секретар|милиционер|участков|следовател|адвокат|нотариус|паренек|девк|девушк|парн|мальчишк|старик|старух|'
                   r'риелтор|риэлтор|юрист|администратор|кассир|коллектор|управляющ|охранник|фотограф|ведущ|официант|медсестр|фельдшер|подруг|коллег|клиентк|регистратор|инженер)')
_REMIND = re.compile(r'тот самый|та самая|того самого|той самой|тому самому|те самые|тех самых|та, что|тот, что|той, что|того, что|тому, что|которого|которая|который|которой|которую', re.I)
_ent = {}
_places = set()
_PLACE_PREP = {'в', 'во', 'из', 'под', 'через', 'до', 'по', 'за'}
_PLACE_NEXT = ('проспект', 'улиц', 'переул', 'бульвар', 'площад', 'шоссе', 'район', 'завод', 'фабрик', 'речк', 'рек', 'вокзал', 'мост', 'остров', 'лини', 'набережн', 'базар', 'ярмарк', 'рын', 'монастыр', 'церк', 'собор', 'станци', 'пристан', 'слобод', 'январ', 'феврал', 'март', 'апрел', 'мая', 'июн', 'июл', 'август', 'сентябр', 'октябр', 'ноябр', 'декабр', 'губерни', 'уезд', 'волост', 'област', 'край', 'кра', 'дорог')
def _find(s):
    while _ent.get(s, s) != s: s = _ent[s]
    return s
_toks = []
_pos = 0
for p in paras:
    italic = p.startswith(('*', '_'))
    for m in re.finditer(r'[А-ЯЁ][а-яё]{2,}', p):
        w = m.group()
        if w.lower().replace('ё', 'е').startswith(_NOTNAME):
            continue
        before = p[:m.start()].rstrip(' *_')
        initial = not before or before[-1] in '.!?…—«(:'
        quoted = italic or p[:m.start()].count('«') > p[:m.start()].count('»')
        prev2 = re.findall(r'[А-Яа-яЁё]+', p[:m.start()])[-1:]
        nxt = re.match(r'\s+([а-яё]+)', p[m.end():])
        place = (bool(prev2) and (prev2[0] in _PLACE_PREP or (prev2[0] == 'на' and re.search(r'(е|ой|ом|ах|ях)$', w))))
        place = place or bool(nxt and nxt.group(1).startswith(_PLACE_NEXT))
        if place:
            _places.add(_stem(w)); continue
        vocative = p.startswith('—') and bool(re.match(r'[,!?]', p[m.end():m.end() + 1])) and before[-1:] in (',', '—', '')
        _toks.append(dict(s=_stem(w), at=_pos + m.start(), initial=initial, skip=quoted or vocative, p=p, a=m.start(), b=m.end()))
    _pos += len(p) + 1
_names = {t['s'] for t in _toks if not t['initial']}
_toks = [t for t in _toks if t['s'] in _names or any(t['s'].endswith(x) and t['s'][:-2] in _names for x in ('ин', 'ын', 'ов', 'ев'))]
for t in _toks:  # притяжательные: Катин, Олиной, Фёдоров → Катя, Оля, Фёдор
    for suf in ('ин', 'ын', 'ов', 'ев'):
        if t['s'].endswith(suf) and t['s'][:-2] in _names:
            t['s'] = t['s'][:-2]
for x, y in zip(_toks, _toks[1:]):  # Матрёна Ивановна, Виктор Андреевич Мерцалов: один человек
    if x['p'] is y['p'] and re.fullmatch(r'\s+', x['p'][x['b']:y['a']]):
        _ent[_find(y['s'])] = _find(x['s'])
_toks = [t for t in _toks if t['s'] not in _places]
_st = sorted({t['s'] for t in _toks}, key=len)
for i, x in enumerate(_st):
    for y in _st[i + 1:]:
        if len(x) >= 4 and y.startswith(x):
            _ent[_find(y)] = _find(x)
_occ = {}
_last = None
for t in _toks:  # имя, отчество и фамилия подряд считаются одним упоминанием
    e = _find(t['s'])
    if not (_last and _last['p'] is t['p'] and _find(_last['s']) == e and re.fullmatch(r'\s+', t['p'][_last['b']:t['a']])):
        _occ.setdefault(e, []).append(t)
    _last = t
_late = []
for s, occ in _occ.items():
    if all(o['initial'] for o in occ) and s not in _names:
        continue
    for k in range(1, min(len(occ), 3)):
        cur_t, prev_t = occ[k], occ[k - 1]
        if cur_t['at'] - prev_t['at'] < _GAP or cur_t['skip'] or cur_t['p'].startswith('—'):
            continue
        p, a, b = cur_t['p'], cur_t['a'], cur_t['b']
        sent_a = max(p.rfind('. ', 0, a), p.rfind('! ', 0, a), p.rfind('? ', 0, a), p.rfind('— ', 0, a)) + 1
        ends = [x for x in (p.find('. ', b), p.find('! ', b), p.find('? ', b)) if x >= 0]
        sent = p[sent_a:(min(ends) + 1 if ends else len(p))].strip(' —')
        prev_w = re.findall(r'[А-Яа-яЁё]+', p[:a])[-1:]
        if prev_w and prev_w[0][0].isupper() and _stem(prev_w[0]) not in _names:  # «Бабка Липа», «Купчиха Сысоева»
            prev_w = [prev_w[0].lower()]
        tail = re.match(r'(\s+[А-ЯЁ][а-яё]+)*', p[b:]).group()
        reminded = (bool(re.match(r',\s*[А-Яа-яЁё]', p[b + len(tail):])) or bool(prev_w and _ROLE.match(prev_w[0].lower().replace('ё', 'е')))
                    or bool(_REMIND.search(sent)))
        if not reminded:
            _late.append(f'{p[a:b]}{tail} (перерыв {(cur_t["at"] - prev_t["at"]) // 1000} тыс. знаков): {sent[:110]}')
        break
_mark = 'OK        ' if not _late else 'ПРОВЕРИТЬ '
print(f'{_mark}Напоминание о вернувшемся герое (Л14): {"нет пропусков" if not _late else len(_late)} '
      f'(норма второстепенный герой через 5 000+ знаков: в той же фразе кто он, «Мерцалову, папенькиному товарищу»; если уместно)')
for x in _late: print('    ', x)

# Имена (с 30.10.2026, СТИЛЬ.md «Имена по эпохе»): тяжёлых имён нет, редких не больше RARE_MAX на рассказ
HEAVY = ('Клеопатра Пульхерия Олимпиада Евлампия Фелицата Евпраксия Агафоклея Секлетея Евлалия Соломонида Манефа Феврония Даздраперма '
         'Евдокия Лукерья Пелагея Агафья Прасковья Матрёна Ефросинья Фёкла Акулина Аграфена Устинья Феодосия Василиса Капитолина Серафима Ираида '
         'Пафнутий Евсевий Савватий Мефодий Ипатий Ферапонт Феоктист Дормидонт Акакий Онуфрий Варлаам Пантелеймон Никифор Евграф Капитон Агафон').split()
RARE = ('Ангелина Эвелина Снежана Милана Виолетта Анжелика Регина Стелла Эльвира Римма Аделина Злата Ярослава Мирослава Станислава Эмилия Каролина Илона '
        'Эдуард Ростислав Святослав Эмиль Ярополк Всеволод').split()
RARE_MAX = 1
def _forms(n):
    if n.endswith('ия'): return n[:-2], r'(?:ия|ии|ию|ией|иею)'
    if n.endswith(('а', 'я')): return n[:-1], r'(?:а|я|ы|и|е|у|ю|ой|ою|ей|ею)'
    if n.endswith(('й', 'ь')): return n[:-1], r'(?:й|ь|я|ю|ем|е|и)'
    return n, r'(?:|а|у|ом|е|ы)'
def _found(names, patronymic=False):
    out = []
    for n in names:
        st, end = _forms(n)
        pat = st + end
        if patronymic:
            pat = '(?:' + pat + '|' + st + r'(?:ович|овна|евич|евна|ьевич|ьевна|ич|ична))'
        if re.search(r'(?<![А-Яа-яЁё])' + pat + r'(?![а-яё])', text):
            out.append(n)
    return out
_author = re.findall(r'(?<![А-Яа-яЁё])(Анастаси[яиюей]|Наст[яиюеёй]|Настен[ьк]\w*)', text)
check(not _author, 'Имя автора канала у героини', 'нет' if not _author else ', '.join(sorted(set(_author))), 'Анастасией и Настей героинь не называть: так зовут автора канала')
_heavy = _found(HEAVY, patronymic=True)
check(not _heavy, 'Тяжёлые имена', 'нет' if not _heavy else ', '.join(_heavy), 'заменить простым именем года рождения: СТИЛЬ.md, «Имена по поколениям»')
_rare = _found(RARE)
check(len(_rare) <= RARE_MAX, 'Редких имён', f'{len(_rare)}' + (f' ({", ".join(_rare)})' if _rare else ''), f'не больше {RARE_MAX} на рассказ')

# Одно место на картинках (с 31.10.2026): если две картинки в одном помещении, паспорт места повторяется дословно
import difflib
_pr = [re.sub(r'\s+', ' ', x).strip() for x in re.findall(r'```(.*?)```', open(path, encoding='utf-8').read(), flags=re.S)]
_pr = [x.replace('wide 16:9 aspect ratio', '').strip() for x in _pr]
if len(_pr) >= 2:
    _suf = os.path.commonprefix([x[::-1] for x in _pr])[::-1]
    _core = [x[:len(x) - len(_suf)] for x in _pr]
    _ROOM = ('kitchen', 'room', 'corridor', 'hallway', 'courtyard', 'dormitory', 'office', 'apartment', 'cafe', 'restaurant', 'dacha', 'garden', 'balcony', 'shop', 'studio')
    _same = []
    for i in range(len(_core)):
        for j in range(i + 1, len(_core)):
            a, b = _core[i].lower(), _core[j].lower()
            if any(w in a and w in b for w in _ROOM):
                m = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
                if m.size < 60:
                    _same.append(f'картинки {i + 1} и {j + 1}: общее место, а общего описания нет')
    _mark = 'OK        ' if not _same else 'ПРОВЕРИТЬ '
    print(f'{_mark}Одно место на картинках: {"паспорт места повторён или места разные" if not _same else len(_same)} (норма если место одно, его описание дословно одинаково во всех промтах)')
    for x in _same: print('    ', x)

print()
print('ИТОГ:', ('всё в норме' if not problems else 'исправить: ' + ', '.join(problems))
      + ('; проверить: напоминание о вернувшемся герое (Л14)' if _late else ''))
