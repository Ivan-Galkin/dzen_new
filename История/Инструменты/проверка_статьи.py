# Проверка статьи канала «Изнанка эпох» по чек-листу из ИНСТРУКЦИЯ.md.
# Запуск из папки История: python3 Инструменты/проверка_статьи.py Статья-69_ГОТОВО-К-ВСТАВКЕ.md
import re, sys

if len(sys.argv) < 2:
    print('Укажите файл статьи'); sys.exit(1)
t = open(sys.argv[1], encoding='utf-8').read()
photos = len(re.findall(r'\*\*\[ФОТО \d', t))
t2 = re.sub(r'```.*?```', '', t, flags=re.S)
lines = [l.strip() for l in t2.split('\n') if l.strip()]
title = lines[0]
skip = []
for i, l in enumerate(lines):
    if l.startswith('**[ФОТО') and 'подлинное' in l:
        skip += [i + 1, i + 2]  # ссылка и подпись под подлинным изображением
paras = []
for i, l in enumerate(lines[1:], start=1):
    if i in skip or l.startswith('**[') or l.startswith('Изображение создано ИИ') or l.startswith('http'):
        continue
    paras.append(l)
cta = 'Если история тронула, поставьте лайк и подпишитесь на канал.'
body = [p for p in paras if p != cta]
text = '\n'.join(body)

sents = []
for p in body:
    for x in re.split(r'(?<=[.!?…])\s+(?=[«А-ЯЁ]|— [А-ЯЁ])', p):
        x = x.strip('— ').strip()
        if x:
            sents.append(x)
wc = [len(re.findall(r'[А-Яа-яЁёA-Za-z0-9-]+', s)) for s in sents]

problems = []
def check(ok, label, value, norm):
    print(('OK        ' if ok else 'ИСПРАВИТЬ ') + f'{label}: {value} (норма {norm})')
    if not ok:
        problems.append(label)

check(6000 <= len(text) <= 8000, 'Знаков', len(text), '6000–8000')
check(30 <= len(body) <= 40, 'Абзацев', len(body), '30–40')
dia = sum(1 for p in body if p.startswith('—') or '— ' in p[:3])
check(5 <= dia <= 10, 'Абзацев с прямой речью', dia, '5–10')
avg = sum(wc) / len(wc) if wc else 0
check(9.5 <= avg <= 12.5, 'Слов в предложении', round(avg, 1), '10–12')
dash = [p[:80] for p in body if not p.startswith('—') and ' — ' in p]
check(not dash, 'Тире в авторском тексте', 'нет' if not dash else len(dash), 'только в репликах')
for d in dash: print('    ', d)
first = body[0] if body else ''
year = re.search(r'\b1\d{3}\b|\b[0-9]{3}\b год', first)
check(not year, 'Дата в первом абзаце', 'нет' if not year else year.group(), 'дат в первом абзаце нет')
check(5 <= photos <= 6, 'Изображений', photos, '5–6')
check('Ссылка:' not in t, 'Слово «Ссылка:»', 'нет' if 'Ссылка:' not in t else 'есть', 'ссылки голой строкой')
check(cta in t, 'Строка призыва', 'есть' if cta in t else 'нет', cta)
check(not re.search(r'^#{1,6} ', t, flags=re.M), 'Подзаголовки', 'нет' if not re.search(r'^#{1,6} ', t, flags=re.M) else 'есть', 'без подзаголовков')
print()
print('ИТОГ:', 'всё в норме' if not problems else 'исправить: ' + ', '.join(problems))
print('Отдельно проверить вручную: каждый факт поиском, подлинные цитаты с источником, ссылки на изображения открываются.')
