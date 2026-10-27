# Проверка рассказа канала «Общая кухня» по числам из ИНСТРУКЦИЯ.md.
# Запуск: python3 проверка_рассказа.py Рассказ-40_ГОТОВО-К-ВСТАВКЕ.md [--глава]
import re, sys

if len(sys.argv) < 2:
    print('Укажите файл рассказа'); sys.exit(1)
path = sys.argv[1]
chapter = '--глава' in sys.argv
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
lo = 8500 if chapter else 9000
check(lo <= n <= 12000, 'Знаков', n, f'{lo}–12000')
check(55 <= len(paras) <= 80, 'Абзацев', len(paras), '55–80')
dia = [p for p in paras if p.startswith('—')]
share = len(dia) / len(paras) if paras else 0
check(0.30 <= share <= 0.50, 'Абзацев-реплик', f'{share:.0%}', '30–50%')
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
    need.append('Спасибо, что дочитали. Если история тронула, поставьте лайк и подпишитесь на канал: здесь каждый день новые истории нашей кухни.')
plain = t.replace('**', '')
miss = [x[:40] for x in need if x not in plain]
check(not miss, 'Обязательные строки', 'все на месте' if not miss else miss, 'подписи к картинкам; строка призыва, а в главе 1 строка «Продолжение истории ниже»')
check(t.count('```') == 6, 'Промтов к картинкам', t.count('```') // 2, '3')


# Против шаблона (с 26.10.2026): слово ЭПИЛОГ, зачин «Было это…», финал-реликвия в сравнении с тремя прошлыми рассказами папки
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
check('ЭПИЛОГ' not in t.split('\n'), 'Слово «ЭПИЛОГ»', 'нет' if 'ЭПИЛОГ' not in t.split('\n') else 'есть',
      'с 26.10.2026 не пишем: перед развязкой через годы ставим ***')
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
    if cur[1] != 1:
        prev3 = [_get(n, 'final') for n in prev]
        bad = _relic(mine) and any(p and _relic(p) for p in prev3)
        check(not bad, 'Финал-вещь', 'повтор' if bad else 'нет повтора', 'вещь-реликвия в последнем абзаце не чаще одного рассказа из четырёх')

print()
print('ИТОГ:', 'всё в норме' if not problems else 'исправить: ' + ', '.join(problems))
