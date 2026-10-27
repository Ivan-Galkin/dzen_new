# Была ли героиня (или её близкие) уже в статьях канала.
# Запуск из папки История: python3 Инструменты/проверка_героинь.py Сакагавея Шарбонно
import sys, glob, re
files = sorted(glob.glob('Статья-*') + glob.glob('ТЕСТ-*_ГОТОВО-К-ВСТАВКЕ.md'))
for name in sys.argv[1:]:
    hits = []
    for f in files:
        t = open(f, encoding='utf-8', errors='ignore').read()
        n = len(re.findall(re.escape(name), t))
        if n:
            hits.append(f'{f.split("_")[0]} ({n})')
    print(f'{name}: ' + (', '.join(hits) if hits else 'не встречалось'))
