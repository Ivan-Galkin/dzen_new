# Копии публикаций под сквозными номерами из ВЫКЛАДКА.md.
# Запуск из папки канала:
#   python3 Инструменты/выкладка.py 27 <папка>        одна публикация
#   python3 Инструменты/выкладка.py 1-26 <папка>      диапазон
# Копия называется Публикация-NN_ГОТОВО-К-ВСТАВКЕ.md, текст не меняется.
import sys, os, re, shutil

if len(sys.argv) != 3:
    sys.exit('Нужно: номер или диапазон и папка, например: 27 /tmp/выкладка')
spec, out = sys.argv[1], sys.argv[2]
a, _, b = spec.partition('-')
nums = range(int(a), int(b or a) + 1)

table = {}
for line in open('ВЫКЛАДКА.md', encoding='utf-8'):
    m = re.match(r'\|\s*(\d+)\s*\|.*\|\s*([^|]*ГОТОВО-К-ВСТАВКЕ\.md)\s*\|\s*$', line)
    if m:
        table[int(m.group(1))] = m.group(2).strip()

os.makedirs(out, exist_ok=True)
for n in nums:
    src = table.get(n)
    if not src or not os.path.exists(src):
        print(f'{n}: файла нет (не написано)')
        continue
    dst = os.path.join(out, f'Публикация-{n:02d}_ГОТОВО-К-ВСТАВКЕ.md')
    shutil.copyfile(src, dst)
    print(f'{n}: {src} -> {dst}')
