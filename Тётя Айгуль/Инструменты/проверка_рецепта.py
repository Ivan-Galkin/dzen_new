# Проверка рецепта и статьи «Кухни мира» канала «Тётя Айгуль» (06.11.2026) по РЕЦЕПТЫ.md и КУХНИ-МИРА.md.
# Запуск из папки канала:
#   python3 Инструменты/проверка_рецепта.py Рецепт-01_ГОТОВО-К-ВСТАВКЕ.md --вид тот-самый --пара
#   python3 Инструменты/проверка_рецепта.py Кухни-01_ГОТОВО-К-ВСТАВКЕ.md --вид кухни
# Виды: блюдо (по умолчанию), тот-самый, хитрости, стол, кухни. --пара: рецепт в паре с рассказом, нужен блок ссылки на рассказ.
import re, sys, os, glob

if len(sys.argv) < 2:
    print('Укажите файл'); sys.exit(1)
path = sys.argv[1]
KINDS = {
    'блюдо':     dict(name='рецепт одного блюда', lo=2000, hi=4500, intro=(400, 1200), steps=(5, 10), tips=2),
    'тот-самый': dict(name='рецепт блюда из рассказа', lo=2000, hi=4500, intro=(400, 1200), steps=(5, 10), tips=2),
    'хитрости':  dict(name='разбор ошибок и рецепт', lo=3500, hi=5500, intro=(400, 2800), steps=(5, 10), tips=2),
    'стол':      dict(name='3–5 блюд к празднику', lo=5000, hi=9000, intro=(300, 1200), steps=(8, 40), tips=1),
    'кухни':     dict(name='кухни мира: история блюда и рецепт', lo=4000, hi=7000, intro=(2500, 5200), steps=(4, 10), tips=1),
}
kind = 'блюдо'
for _i, _a in enumerate(sys.argv):
    if _a.startswith('--вид='):
        kind = _a.split('=', 1)[1]
    elif _a == '--вид' and _i + 1 < len(sys.argv):
        kind = sys.argv[_i + 1]
kind = kind.strip().lower()
if kind == 'рецепт':
    kind = 'блюдо'
if kind not in KINDS:
    print('Неизвестный вид:', kind, '| есть:', ', '.join(KINDS)); sys.exit(1)
pair = '--пара' in sys.argv
K = KINDS[kind]
print(f'Вид: {kind} ({K["name"]})' + ('; пара с рассказом' if pair else ''))

raw = open(path, encoding='utf-8').read()
t = re.sub(r'\*\*\[.*?\]\*\*', '', raw)
t = re.sub(r'```.*?```', '', t, flags=re.S)
t = t.replace('Подпись: Изображение создано ИИ', '')
lines = [l.strip() for l in t.split('\n') if l.strip()]
title = raw.split('\n')[0].replace('**', '').strip().lstrip('#').strip()
body = lines[1:]

problems, soft = [], []
def check(ok, label, value, norm):
    print(f'{"OK        " if ok else "ИСПРАВИТЬ "}{label}: {value} (норма {norm})')
    if not ok:
        problems.append(label)
def note(text):
    print('ПРОВЕРИТЬ ' + text)
    soft.append(text.split(':')[0])

def find(prefix):
    for i, l in enumerate(body):
        if l.lower().startswith(prefix):
            return i
    return None
i_ing, i_how, i_tip = find('что понадобится'), find('как готовлю'), find('мои хитрости')
check(i_ing is not None and i_how is not None and i_tip is not None and i_ing < i_how < i_tip,
      'Разделы', 'на месте' if (i_ing is not None and i_how is not None and i_tip is not None and i_ing < i_how < i_tip) else 'нет или не по порядку',
      '«Что понадобится (на N порций):», «Как готовлю:», «Мои хитрости:» отдельными строками по порядку')

service = ('Ваша тётя Айгуль', 'А историю, из-за которой', 'А историю, с которой', 'А рассказ, из-за которого')
text_all = '\n'.join(l for l in body if not l.startswith(service))
n = len(text_all)
check(K['lo'] <= n <= K['hi'], 'Знаков', n, f'{K["lo"]}–{K["hi"]}')

if i_ing is not None:
    intro = [l for l in body[:i_ing]]
    il = len(' '.join(intro))
    lo, hi = K['intro']
    check(lo <= il <= hi, 'Знаков до рецепта' if kind == 'кухни' else 'Зачин', il, f'{lo}–{hi}')
    if kind != 'кухни':
        dg = re.findall(r'\d+', ' '.join(intro))
        check(not dg, 'Цифры в зачине', 'нет' if not dg else dg, 'в зачине числа словами; цифры в списке и шагах')
    else:
        heads = [l for l in intro[1:] if len(l) <= 70 and not re.search(r'[.!?…:»]$', l) and not l.startswith(('—', '-'))]
        check(3 <= len(heads) <= 6, 'Подзаголовков в истории', len(heads), '3–5 коротких строк без точки')
        dg = [x for x in re.findall(r'\d+', ' '.join(intro)) if not re.fullmatch(r'1[0-9]{3}|20[0-2][0-9]', x)]
        check(not dg, 'Цифры в истории', 'нет' if not dg else dg[:8], 'годы цифрами можно, остальные числа словами')
    if i_how is not None:
        ing = [l for l in body[i_ing + 1:i_how] if l.startswith(('- ', '• '))]
        check(len(ing) >= 3, 'Продуктов в списке', len(ing), 'от 3, каждый строкой «- 500 г …»')
        noamt = [l for l in ing if not re.search(r'\d|по вкусу|щепот|пучок|горст|для смазки|для жарки|для подачи|немного|веточ', l)]
        check(not noamt, 'Продукты без количества', 'нет' if not noamt else '; '.join(x[:40] for x in noamt[:4]), 'у каждого количество или «по вкусу»')
        m = re.search(r'на\s+(\d+|[а-яё]+)\s+порц|на\s+(\d+|[а-яё]+)\s+(штук|человек)|на\s+форму|выход', body[i_ing].lower())
        check(bool(m), 'Порции', 'указаны' if m else 'нет', '«Что понадобится (на 6 порций):» или на форму, выход')
        if i_tip is not None:
            steps = [l for l in body[i_how + 1:i_tip] if re.match(r'\d+[.)]\s', l)]
            lo, hi = K['steps']
            check(lo <= len(steps) <= hi, 'Шагов', len(steps), f'{lo}–{hi}, нумерованные «1. …»')
            joined = ' '.join(steps).lower()
            if re.search(r'духовк|запека|выпека|печь', joined):
                ok = bool(re.search(r'\d+\s*(градус|°)', joined))
                check(ok, 'Температура духовки', 'есть' if ok else 'нет', 'в шаге с духовкой градусы и время')
            ok = bool(re.search(r'\d+\s*(минут|мин\b|час)', joined))
            check(ok, 'Время в шагах', 'есть' if ok else 'нет', 'сколько варить, жарить, томить')
            tips = [l for l in body[i_tip + 1:] if l.startswith(('- ', '• '))]
            check(len(tips) >= K['tips'], 'Хитростей', len(tips), f'не меньше {K["tips"]}')

nar = [l for l in body if not l.startswith(('—', '- ', '• ')) and not re.match(r'\d+[.)]\s', l)]
em = [l[:70] for l in body if not l.startswith('—') and '—' in l]
en = [l[:70] for l in body if not l.startswith('—') and re.search(r'(?<!\d)\s*–\s*(?!\d)', l)]
check(not em and not en, 'Тире вне реплик', 'нет' if not (em or en) else len(em) + len(en), 'тире только в репликах; диапазон «3–4 минуты» можно')
for x in (em + en)[:5]:
    print('    ', x)
check('"' not in text_all, 'Прямые кавычки', 'нет' if '"' not in text_all else 'есть', 'только «ёлочки»')

low = text_all.lower()
health = sorted(set(re.findall(r'полезн\w*|лечит|лечеб\w*|снижа\w* (?:давлен|холестерин|сахар)\w*|очищает|детокс\w*|похуде\w*|сжига\w* жир|иммунитет\w*|витамин\w*', low)))
check(not health, 'Обещания здоровья', 'нет' if not health else ', '.join(health), 'без «полезно», «лечит», «снижает»: можно «сытно», «легко», «постное»')
_BRANDS = ['сбербанк', 'тинькоф', 'озон', 'ozon', 'вайлдберри', 'wildberries', 'авито', 'яндекс', 'ватсап', 'whatsapp', 'телеграм', 'telegram',
           'пятёрочк', 'перекрёст', 'ашан', 'philips', 'redmond', 'тефаль', 'tefal', 'простоквашино', 'домик в деревне', 'макфа',
           'мистраль', 'хайнц', 'heinz', 'calve', 'кальве', 'maggi', 'кнорр', 'knorr', 'valio', 'валио', 'кока-кол', 'coca', 'пепси', 'pepsi',
           'нескафе', 'nescafe', 'липтон', 'lipton', 'гринфилд', 'нутелл', 'nutella', 'барилл', 'barilla', 'махеев', 'коровка из кореновки', 'увелка']
br = sorted({b for b in _BRANDS if re.search(r'(?<![а-яёa-z])' + re.escape(b), low)})
check(not br, 'Бренды', 'нет' if not br else ', '.join(br), 'без марок продуктов, техники, магазинов')
stamps = ['однако', 'является', 'данный', 'стоит отметить', 'не секрет', 'безусловно', 'нереально вкусн', 'просто бомба', 'пальчики оближешь', 'вкуснотища']
st = [w for w in stamps if w in low]
check(not st, 'Штампы', 'нет' if not st else ', '.join(st), 'заменить живой фразой')
cute = len(re.findall(r'вкусняшк|кушать|кушаем|лучок|сольц|сахарок|маслиц', low))
check(cute <= 1, 'Уменьшительные и «кушать»', cute, 'не больше одного на статью')
dear = low.count('мои дорогие') + low.count('дорогие мои')
check(dear <= 1, '«Мои дорогие»', dear, 'один раз на статью')
ex = text_all.count('!')
check(ex <= 3, 'Восклицательных знаков', ex, 'не больше трёх в тексте')

if re.search(r'заготов|на зиму|закат|стерилиз|консерв', low):
    note('Заготовка: пропорции уксуса, соли и сахара по проверенному источнику, стерилизация или кипящая заливка; грибы и чеснок в масле на хранение не советовать')
if re.search(r'сыр(ые|ых|ой) (яйц|желт|белк)', low):
    note('Сырые яйца: в блюдах без готовки не использовать')
if re.search(r'свинин|фарш|куриц|курин', low) and not re.search(r'прозрачн|готовност|сок\b|прокол|термометр', low):
    note('Мясо и птица: сказать, как понять готовность (прозрачный сок, прокол, разрез)')
if re.search(r'орех|арахис|кунжут', low) and 'аллерг' not in low:
    note('Орехи или кунжут: подсказать замену на случай аллергии')

tail = body[-4:]
q = any('?' in l for l in tail)
check(q, 'Вопрос читательницам', 'есть' if q else 'нет', 'один конкретный вопрос в конце')
need = ['Подпись: Изображение создано ИИ', 'wide 16:9 aspect ratio', 'Ваша тётя Айгуль']
if pair:
    need.append('[ССЫЛКА — рассказ')
plain = raw.replace('**', '')
miss = [x for x in need if x not in plain]
check(not miss, 'Обязательные строки', 'все на месте' if not miss else miss, 'подпись к обложке, подпись «Ваша тётя Айгуль»; с --пара блок ссылки на рассказ')
check(raw.count('```') == 2, 'Промтов к картинкам', raw.count('```') // 2, '1: только обложка')
check(raw.count('**[ФОТО') == 1, 'Блоков ФОТО', raw.count('**[ФОТО'), '1')

tw = len(re.findall(r'[А-Яа-яЁё-]+', title))
check(10 <= tw <= 18, 'Слов в заголовке', tw, '10–18')
check(title.count('!') <= 1, 'Восклицательных в заголовке', title.count('!'), 'не больше одного')
caps = re.findall(r'\b[А-ЯЁ]{4,}\b', title)
check(not caps, 'Капслок в заголовке', 'нет' if not caps else caps, 'без слов капслоком')
emo = re.findall(r'[\U0001F300-\U0001FAFF☀-➿]', raw)
check(not emo, 'Эмодзи', 'нет' if not emo else len(emo), 'без эмодзи')
if 'секрет' in title.lower():
    note('«Секрет» в заголовке: не чаще одного рецепта из пяти (Карта-заголовков.md)')

def _tnorm(s):
    s = re.sub(r'\.\s*Глава\s*\d+\s*$', '', s.replace('**', '').strip().lstrip('#').strip())
    return ' '.join(re.findall(r'[а-яa-z0-9]+', s.lower().replace('ё', 'е')))
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_me = os.path.abspath(path)
dups = []
for pat in ('Рассказ-*_ГОТОВО-К-ВСТАВКЕ.md', 'Рецепт-*_ГОТОВО-К-ВСТАВКЕ.md', 'Кухни-*_ГОТОВО-К-ВСТАВКЕ.md'):
    for f in glob.glob(os.path.join(_root, '*', pat)):
        if os.path.abspath(f) == _me:
            continue
        try:
            other = open(f, encoding='utf-8').readline()
        except OSError:
            continue
        if _tnorm(other) == _tnorm(title):
            dups.append(f'{os.path.basename(os.path.dirname(f))}, {os.path.basename(f).split("_")[0]}')
check(not dups, 'Заголовок уже был', 'нет' if not dups else '; '.join(dups), 'дословно не повторять ни в одном нашем канале')

print()
print('ИТОГ:', ('всё в норме' if not problems else 'исправить: ' + ', '.join(problems))
      + (('; проверить: ' + ', '.join(soft)) if soft else ''))
