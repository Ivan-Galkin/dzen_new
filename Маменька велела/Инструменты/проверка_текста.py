# Проверка рассказа по числам ритма канала «Маменька велела».
# Запуск: python проверка_текста.py Рассказ-01_ГОТОВО-К-ВСТАВКЕ.md
# Служебные блоки (промты, ссылки, подписи, строка призыва) не считаются.
# Цели: 9 000–12 000 знаков (глава 8 500–12 000), реплик 30–50% абзацев,
# 8–9 слов в предложении, длинных (11+ слов) не больше 30%,
# не больше 3 коротких и 2 длинных подряд, тире в авторском тексте ноль,
# цифры только в документах внутри текста.
import re, sys

t = open(sys.argv[1], encoding='utf-8').read()
t2 = re.sub(r'\*\*\[.*?\]\*\*', '', t)
t2 = re.sub(r'```.*?```', '', t2, flags=re.S)
t2 = re.sub(r'Подпись: Изображение создано ИИ', '', t2)
lines = [l.strip() for l in t2.split('\n') if l.strip()]
body = [l for l in lines[1:] if not l.startswith('Спасибо, что дочитали')]
paras = [l for l in body if l not in ('***', 'ЭПИЛОГ')]
text = '\n'.join(paras)

print('Знаков:', len(text))
print('Абзацев:', len(paras))
dia = [p for p in paras if p.startswith('—')]
print('Абзацев-реплик:', len(dia), f'({len(dia)/len(paras):.0%})')

sents = []
for p in paras:
    for x in re.split(r'(?<=[.!?…])\s+(?=[«А-ЯЁ]|— [А-ЯЁ])', p):
        x = x.strip('— ').strip()
        if x:
            sents.append(x)
wc = [len(re.findall(r'[А-Яа-яЁёA-Za-z0-9-]+', s)) for s in sents]
print('Предложений:', len(sents), '| слов в среднем:', round(sum(wc)/len(wc), 2))
long_ = sum(1 for w in wc if w >= 11)
short = sum(1 for w in wc if w <= 5)
print(f'Длинных (11+): {long_/len(wc):.0%} | коротких (до 5): {short/len(wc):.0%}')

run_s = run_l = ms = ml = 0
for w in wc:
    run_s = run_s + 1 if w <= 5 else 0
    run_l = run_l + 1 if w >= 11 else 0
    ms, ml = max(ms, run_s), max(ml, run_l)
print('Подряд коротких, максимум:', ms, '| подряд длинных, максимум:', ml)

bad = [p[:80] for p in paras if not p.startswith('—') and '—' in p]
print('Тире в авторском тексте:', bad if bad else 'нет')
print('Цифры:', re.findall(r'\d+', text) or 'нет')
lat = re.findall(r'[A-Za-z]{2,}', text)
print('Латиница (французские слова писать по-русски):', lat if lat else 'нет')
for w in ['однако', 'является', 'данный', 'стоит отметить', 'ком в горле', 'время словно остановилось']:
    if w in text.lower():
        print('Штамп:', w)
if re.search(r'(?<![а-яё])затем(?![а-яё])', text.lower()):
    print('Штамп: затем')

for k in range(len(wc) - 2):
    if wc[k] >= 11 and wc[k+1] >= 11 and wc[k+2] >= 11:
        print('3 длинных подряд:', sents[k][:60])
for k in range(len(wc) - 3):
    if all(wc[k+j] <= 5 for j in range(4)):
        print('4 коротких подряд:', sents[k][:40], '|', sents[k+3][:40])
