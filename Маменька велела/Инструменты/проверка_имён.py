# Проверка, встречались ли имена в прошлых рассказах.
# Запуск из папки Рассказы: python3 Инструменты/проверка_имён.py Лиза Захар Мавра
import sys, glob, re
files = sorted(glob.glob('Рассказ-*.md'))
for name in sys.argv[1:]:
    hits = []
    for f in files:
        t = open(f, encoding='utf-8').read()
        n = len(re.findall(r'(?<![А-Яа-яЁё])' + re.escape(name), t))
        if n:
            hits.append(f'{f.split("_")[0]} ({n})')
    print(f'{name}: ' + (', '.join(hits) if hits else 'не встречалось'))
