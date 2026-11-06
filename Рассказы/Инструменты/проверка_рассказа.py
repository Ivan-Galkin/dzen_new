# Проверка рассказа канала «Свои и чужие» по числам из ИНСТРУКЦИЯ.md и Формы_рассказов.md.
# Запуск: python3 проверка_рассказа.py Рассказ-40_ГОТОВО-К-ВСТАВКЕ.md [--форма повесть] [--глава]
import re, sys

if len(sys.argv) < 2:
    print('Укажите файл рассказа'); sys.exit(1)
path = sys.argv[1]
chapter = '--глава' in sys.argv

# Формы рассказа (с 30.10.2026): правила в Формы_рассказов.md. Без --форма проверяется классический рассказ.
# Запуск: python3 проверка_рассказа.py Рассказ-50_ГОТОВО-К-ВСТАВКЕ.md --форма повесть [--глава]
FORMS = {
    'рассказ':   dict(name='классический рассказ', lo=9000,  hi=12000, paras=(55, 80),  dia=(0.30, 0.50), first=False),
    'повесть':   dict(name='повесть в одной статье', lo=15000, hi=20000, paras=(90, 135), dia=(0.30, 0.50), first=False),
    'линии':     dict(name='две линии',            lo=15000, hi=25000, paras=(90, 165), dia=(0.30, 0.50), first=False),
    'хроника':   dict(name='тогда и сейчас: хроника', lo=9000, hi=18000, paras=(45, 120), dia=(0.15, 0.50), first=False),
    'перебивка': dict(name='тогда и сейчас: перебивка', lo=15000, hi=25000, paras=(90, 165), dia=(0.30, 0.50), first=False),
    'исповедь':  dict(name='исповедь, первое лицо', lo=15000, hi=20000, paras=(90, 135), dia=(0.30, 0.50), first=True),
    'глаза':     dict(name='глазами другого (разовый тест)', lo=12000, hi=18000, paras=(70, 120), dia=(0.30, 0.50), first=True),
    'ошиблась':  dict(name='ошиблась в человеке (разовый тест)', lo=9000, hi=20000, paras=(55, 135), dia=(0.30, 0.50), first=False),
    'длинная':   dict(name='длинная повесть (тест с 07.11.2026)', lo=24000, hi=32000, paras=(145, 215), dia=(0.30, 0.50), first=False),
}
form = 'рассказ'
for _i, _a in enumerate(sys.argv):
    if _a.startswith('--форма='):
        form = _a.split('=', 1)[1]
    elif _a == '--форма' and _i + 1 < len(sys.argv):
        form = sys.argv[_i + 1]
form = form.strip().lower()
if form not in FORMS:
    print('Неизвестная форма:', form, '| есть:', ', '.join(FORMS)); sys.exit(1)
P = FORMS[form]
print(f'Форма: {form} ({P["name"]})' + ('; глава' if chapter else ''))
t = open(path, encoding='utf-8').read()
# Разделитель частей (с 06.11.2026): в файле пишется \*\*\*, чтобы при копировании из просмотра Markdown остались звёздочки
_bare = sum(1 for l in t.split('\n') if l.strip() == '***')
t = '\n'.join('***' if l.strip() == r'\*\*\*' else l for l in t.split('\n'))

t2 = re.sub(r'\*\*\[.*?\]\*\*', '', t)
t2 = re.sub(r'```.*?```', '', t2, flags=re.S)
t2 = re.sub(r'Подпись: Изображение создано ИИ', '', t2)
lines = [l.strip() for l in t2.split('\n') if l.strip()]
service = ('Спасибо, что дочитали', 'Продолжение истории ниже', 'Начало истории здесь')
body = [l for l in lines[1:] if not l.startswith(service)]
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

check(_bare == 0, 'Разделитель частей', 'записан как \\*\\*\\*' if _bare == 0 else f'голых *** строк: {_bare}', 'в файле \\*\\*\\*, иначе при копировании из просмотра звёздочки пропадут')

n = len(text)
lo, hi = (8500, 12000) if chapter else (P['lo'], P['hi'])
pl, ph = (55, 80) if chapter else P['paras']
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
if P['first']:
    check(fp >= 1.5, '«Я» рассказчицы в повествовании', f'{fp:.1f} на 100 слов', 'не меньше 1,5: форма от первого лица')
else:
    check(fp <= 1.0, '«Я» в повествовании', f'{fp:.1f} на 100 слов', 'третье лицо: «я» только в репликах и письмах')
avg = sum(wc) / len(wc) if wc else 0
check(7.5 <= avg <= 9.5, 'Слов в предложении', round(avg, 2), '8–9, допустимо 7,5–9,5')
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
          'сердце', 'слеза', 'слёзы', 'повисла тишина', 'мир рухнул', 'внутри всё оборвалось', 'с замиранием']
found = [w for w in stamps if w in text.lower()]
if re.search(r'(?<![а-яё])затем(?![а-яё])', text.lower()): found.append('затем')
check(not found, 'Штампы', 'нет' if not found else ', '.join(found), 'заменить действием или деталью')

need = ['Подпись: Изображение создано ИИ', 'wide 16:9 aspect ratio']
first_chapter = chapter and '. Глава 2' not in t.split('\n')[0]
if first_chapter:
    need.append('Продолжение истории ниже')
else:
    need.append('Спасибо, что дочитали. Если история тронула, поставьте лайк и подпишитесь на канал: каждый день здесь новый рассказ о женских судьбах советской деревни.')
miss = [x[:40] for x in need if x not in t]
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
    return [l for l in ls[1:] if not l.startswith(service) and l not in ('***', r'\*\*\*', 'ЭПИЛОГ')]
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
            'ключ', 'заречь', 'ольхов', 'ольшанк', 'покровск', 'москв', 'ленинград', 'росси', 'волг', 'сибир', 'урал', 'кавказ', 'крым', 'петербург',
            'киев', 'казан', 'саратов', 'пенз', 'берлин', 'германи', 'ведомост', 'губернск', 'правд', 'известия', 'советск', 'союз', 'ссср', 'родин')
_ROLE = re.compile(r'(майор|дяд|тет|нян|предводител|председател|судь|старост|свекров|свекр|золовк|девер|невестк|снох|сосед|бригадир|учител|фельдшер|доктор|врач|'
                   r'батюшк|поп|барин|барын|барышн|купец|купц|купчих|приказчик|исправник|управляющ|инспектор|директор|парторг|агроном|почтальон|кум|крестн|'
                   r'внук|внучк|брат|сестр|отец|отц|мать|матер|муж|жен|вдов|шофер|тракторист|кладовщик|счетовод|продавщиц|завмаг|лесник|пастух|кузнец|мельник|конюх|'
                   r'повитух|сын|доч|зят|тест|тещ|племянни|падчериц|пасын|мачех|отчим|мельничих|стар|помещиц|полковниц|генеральш|дворнич|портних|почтмейстер|ротмистр|штабс|кухарк|горничн|ключниц|экономк|гувернантк|сват|кучер|'
                   r'бабк|бабушк|дед|товарищ|друг|подруг|заседател|офицер|полковник|генерал|капитан|поручик|денщик|солдат|унтер|писар|урядник|лавочник|'
                   r'мастер|начальник|комендант|вахтер|дворник|секретар|милиционер|участков|следовател|адвокат|нотариус|паренек|девк|девушк|парн|мальчишк|старик|старух)')
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
HEAVY = ('Клеопатра Пульхерия Олимпиада Евлампия Фелицата Евпраксия Агафоклея Секлетинья Секлетея Евлалия Соломонида Юлиания Ксаверия Агапея '
         'Манефа Феврония Голиндуха Епистимия Платонида Евстолия Конкордия Сосипатра Мелитина Даздраперма '
         'Пафнутий Евсевий Савватий Маврикий Виссарион Нифонт Мефодий Ипатий Евстратий Варсонофий Ферапонт Феоктист Дормидонт Мардарий '
         'Евтихий Акакий Зосима Онуфрий Варлаам Агапит Мисаил Иоанникий Пантелеймон').split()
RARE = ('Калерия Изольда Нинель Элеонора Вилен Владлен Марлен Октябрина Сталина Ревмира Эра Ираида Серафима Ангелина Аглая Агриппина Ефросинья Евсей Федора Феодосия Капитолина Василиса Эмма Эльза Леокадия Виринея Харитина Стефанида Улита Лукерья Августа Иветта Модест Венедикт Гурий Харитон Васса Ядвига Эвелина Марианна Ванда Илона Домника Домна Феликс Назар Елисей Ерофей Аким Никифор Евграф Аристарх Поликсена Ариадна Антонида Нонна').split()
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
_heavy = _found(HEAVY, patronymic=True)
check(not _heavy, 'Тяжёлые имена', 'нет' if not _heavy else ', '.join(_heavy), 'заменить простым именем поколения: СТИЛЬ.md, «Имена по эпохе»')
_rare = _found(RARE)
check(len(_rare) <= RARE_MAX, 'Редких имён', f'{len(_rare)}' + (f' ({", ".join(_rare)})' if _rare else ''), f'не больше {RARE_MAX} на рассказ')

# Одно место на картинках (с 31.10.2026): если две картинки в одном помещении, паспорт места повторяется дословно
import difflib
_pr = [re.sub(r'\s+', ' ', x).strip() for x in re.findall(r'```(.*?)```', open(path, encoding='utf-8').read(), flags=re.S)]
_pr = [x.replace('wide 16:9 aspect ratio', '').strip() for x in _pr]
if len(_pr) >= 2:
    _suf = os.path.commonprefix([x[::-1] for x in _pr])[::-1]
    _core = [x[:len(x) - len(_suf)] for x in _pr]
    _ROOM = ('kitchen', 'izba', 'hut', 'room', 'parlour', 'parlor', 'chamber', 'corridor', 'hallway', 'courtyard', 'dormitory', 'barrack', 'office')
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

# Дословный повтор заголовка (с 07.11.2026, решение владельца 06.11): заголовок не должен совпадать
# с заголовком любого рассказа во всех папках каналов. Похожие слова в соседних каналах можно.
def _tnorm(s):
    s = re.sub(r'\.\s*Глава\s*\d+\s*$', '', s.replace('**', '').strip().lstrip('#').strip())
    return ' '.join(re.findall(r'[а-яa-z0-9]+', s.lower().replace('ё', 'е')))
def _ttitle(fn):
    try:
        return open(fn, encoding='utf-8').readline().replace('**', '').strip().lstrip('#').strip()
    except OSError:
        return ''
_title = open(path, encoding='utf-8').readline().replace('**', '').strip().lstrip('#').strip()
_me = os.path.abspath(path)
_mynum = _num(path)
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_dups = []
for _f in glob.glob(os.path.join(_root, '*', 'Рассказ-*_ГОТОВО-К-ВСТАВКЕ.md')):
    _f = os.path.abspath(_f)
    if _f == _me:
        continue
    if os.path.dirname(_f) == os.path.dirname(_me) and _mynum and _num(_f) and _num(_f)[0] == _mynum[0]:
        continue  # другая глава той же истории
    if _tnorm(_ttitle(_f)) == _tnorm(_title):
        _dups.append(f'{os.path.basename(os.path.dirname(_f))}, {os.path.basename(_f).split("_")[0]}')
check(not _dups, 'Заголовок уже был', 'нет' if not _dups else '; '.join(_dups), 'дословно не повторять ни в одном нашем канале')

# Заголовки внутри канала и ТЕСТ-11 (с 07.11.2026, Карта-заголовков.md, раздел 0).
TITLE_KINDS = ['поговорка', 'срок', 'действие']
TITLE_PER_KIND = 4
TITLE_TEST_FROM = 90
_tkind = None
for _i, _a in enumerate(sys.argv):
    if _a.startswith('--заголовок='):
        _tkind = _a.split('=', 1)[1].strip().lower()
    elif _a == '--заголовок' and _i + 1 < len(sys.argv):
        _tkind = sys.argv[_i + 1].strip().lower()
if _tkind and _tkind not in TITLE_KINDS:
    print('Неизвестный вид заголовка:', _tkind, '| есть:', ', '.join(TITLE_KINDS)); sys.exit(1)
_TEND = ('ами', 'ями', 'ого', 'его', 'ому', 'ему', 'ыми', 'ими', 'ья', 'ье', 'ьи', 'ью', 'ая', 'яя', 'ое', 'ее', 'ые', 'ие',
         'ый', 'ий', 'ой', 'ей', 'ом', 'ем', 'ах', 'ях', 'ам', 'ям', 'ов', 'ев', 'ую', 'юю',
         'а', 'я', 'ы', 'и', 'у', 'ю', 'е', 'о', 'ь', 'й')
_TSTOP = {'через', 'после', 'перед', 'между', 'около', 'возле', 'вместо', 'кроме', 'среди', 'против', 'чтобы', 'когда', 'тоже', 'себя', 'свой', 'своя', 'свою', 'своей'}
# «Невеста» поднимает CTR (октябрь: Маменька 1,59, Свои 1,33, Кухня 1,29 медианы канала): можно один заголовок из трёх.
_TFREE = {'невес'}
_TSYN = {'мат': 'мать', 'матер': 'мать', 'доч': 'дочь', 'дочер': 'дочь', 'дочк': 'дочь', 'дочен': 'дочь'}
def _tname(s): return bool(re.match(r'^[А-ЯЁ][а-яё]+\.\s', s))
def _tstems(s):
    s = re.sub(r'\.\s*Глава\s*\d+\s*$', '', s)
    m = re.match(r'^[А-ЯЁ][а-яё]+\.\s+', s)
    if m: s = s[m.end():]
    out = {}
    for w0 in re.findall(r'[а-яё]+', s.lower().replace('ё', 'е')):
        if len(w0) < 4 or w0 in _TSTOP: continue
        w = w0
        for e in _TEND:
            if w.endswith(e) and len(w) - len(e) >= 3:
                w = w[:-len(e)]; break
        w = w[:5]
        out[_TSYN.get(w, w)] = w0
    return out
_TDEF = re.compile(r'хром|(^|\s)нем(ая|ой|ую|ого|ые)(\s|$)|глух|слеп|калек|безрук|безног|(^|\s)кос(ая|ой|ую)(\s|$)|(^|\s)крив(ая|ой|ую)(\s|$)'
                   r'|горбат|горбун|(^|\s)ряб(ая|ой|ую)(\s|$)|поводыр|глазлив|увеч|одноглаз|косоглаз|заик|убог')
def _tdef(s): return bool(_TDEF.search(s.lower().replace('ё', 'е')))
_tsoft = []
if _mynum:
    _prevt = {}
    for _f in glob.glob(os.path.join(os.path.dirname(_me), 'Рассказ-*_ГОТОВО-К-ВСТАВКЕ.md')):
        _n = _num(_f)
        if _n and _n[0] < _mynum[0] and (_n[0] not in _prevt or _n[1] < _prevt[_n[0]][0]):
            _prevt[_n[0]] = (_n[1], _ttitle(_f))
    _prev = [_prevt[k][1] for k in sorted(_prevt)][-14:]
    _mine = _tstems(_title)
    _hit = []
    for _j, _p in enumerate(_prev[-6:]):
        _near = _j >= len(_prev[-6:]) - 2
        _same = sorted(_mine[k] for k in set(_mine) & set(_tstems(_p)) if _near or k not in _TFREE)
        if _same: _hit.append(f'«{", ".join(_same)}» было в «{_p}»')
    check(not _hit, 'Слово заголовка в шести прошлых', 'нет' if not _hit else '; '.join(_hit), 'главное слово не чаще одного заголовка из семи')
    _bad = _tname(_title) and any(_tname(x) for x in _prev[-7:])
    check(not _bad, '«Имя. Суть»', 'повтор' if _bad else ('есть' if _tname(_title) else 'нет'), 'не чаще одного заголовка из восьми')
    _bad = _tdef(_title) and any(_tdef(x) for x in _prev[-14:])
    check(not _bad, 'Увечье в заголовке', 'повтор' if _bad else ('есть' if _tdef(_title) else 'нет'), 'не чаще одного заголовка из пятнадцати')
_tw = len(re.findall(r'[А-Яа-яЁё-]+', re.sub(r'\.\s*Глава\s*\d+\s*$', '', _title)))
_lo, _hi = (4, 7) if _tkind == 'действие' else ((2, 5) if _tkind else (1, 5))
check(_lo <= _tw <= _hi, 'Слов в заголовке', _tw, f'{_lo}–{_hi}' + (f' (тест: {_tkind})' if _tkind else ''))
# ТЕСТ-11: тестовый заголовок у рассказа, если у двух прошлых в таблице нет «тест:». Вид по очереди TITLE_KINDS.
if _mynum and _mynum[0] >= TITLE_TEST_FROM and _mynum[1] != 2:
    _tt, _col = {}, None
    _tab = os.path.join(os.path.dirname(_me), '00_НАЧНИ-ОТСЮДА.md')
    if os.path.exists(_tab):
        for _line in open(_tab, encoding='utf-8'):
            if not _line.startswith('|'): continue
            _c = [x.strip() for x in _line.strip().strip('|').split('|')]
            if 'Тип заголовка' in _c: _col = _c.index('Тип заголовка'); continue
            if _c and _c[0] == '№': _col = None; continue
            if _col is not None and re.fullmatch(r'\d+', _c[0]) and len(_c) > _col:
                _tt[int(_c[0])] = _c[_col]
    _done = [_tt[k] for k in sorted(_tt) if TITLE_TEST_FROM <= k < _mynum[0] and 'тест:' in _tt[k]]
    _last2 = [_tt[k] for k in sorted(k for k in _tt if k < _mynum[0])][-2:]
    _due = not any('тест:' in x for x in _last2)
    if len(_done) >= len(TITLE_KINDS) * TITLE_PER_KIND:
        print(f'OK        ТЕСТ-11: набран ({len(_done)} заголовков), ждём итога, обычные заголовки')
        if _tkind: check(False, 'ТЕСТ-11', 'тест уже набран', 'вид заголовка не указывать')
    else:
        _next = TITLE_KINDS[len(_done) % len(TITLE_KINDS)]
        if _tkind and form == 'длинная':
            check(False, 'ТЕСТ-11', 'тестовый заголовок на длинной повести', 'одна проверка на статью: тест переносится на следующий рассказ')
        elif form == 'длинная':
            print('OK        ТЕСТ-11: длинная повесть, тестовый заголовок переносится на следующий рассказ')
        elif _tkind:
            check(_tkind == _next, 'Вид тестового заголовка', _tkind, f'по очереди сейчас «{_next}»')
            check(_due, 'Тестовый заголовок по очереди', 'да' if _due else 'тест был в одном из двух прошлых', 'один рассказ из трёх')
        elif _mynum[1] == 1:
            print('OK        ТЕСТ-11: две главы, тестовый заголовок переносится на следующий рассказ')
        elif _due:
            print(f'ПРОВЕРИТЬ ТЕСТ-11: этот рассказ тестовый, вид «{_next}», запуск с --заголовок {_next}. '
                  'Если рассказ в другом тесте (ТЕСТ-10, продолжение С-04), тест переносится на следующий.')
            _tsoft.append(f'тестовый заголовок «{_next}» (ТЕСТ-11)')

# Числа (с 06.11.2026, Логика_повествования.md, Л20): модуль проверка_чисел.py рядом с этим скриптом
_chisla = []
try:
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location('proverka_chisel', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'проверка_чисел.py'))
    _cm = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_cm)
    _ch, _chisla = _cm.report(paras)
    check(not _ch, 'Числа (Л20)', '; '.join(_ch) if _ch else 'невозможных нет', 'пальцев не больше десяти; части в сумме дают целое')
    for _x in _chisla:
        print('ПРОВЕРИТЬ Числа (Л20):', _x)
except FileNotFoundError:
    print('ПРОВЕРИТЬ Числа (Л20): нет файла проверка_чисел.py рядом со скриптом')

print()
print('ИТОГ:', ('всё в норме' if not problems else 'исправить: ' + ', '.join(problems))
      + ((f'; проверить: числа (Л20), строк выше: {len(_chisla)}') if _chisla else '')
      + ('; проверить: напоминание о вернувшемся герое (Л14)' if _late else '')
      + (('; проверить: ' + ', '.join(_tsoft)) if _tsoft else ''))
