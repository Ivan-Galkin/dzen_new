# Проверка имён героини и обидчика (СТИЛЬ.md «Имена по поколениям», канал «Тётя Айгуль»).
# Повторять имена между рассказами можно. Нельзя только брать для героини
# и обидчика имя, которое было в пятнадцати последних рассказах (с 16.11.2026, решение владельца).
# Запуск из папки канала ДО сохранения нового рассказа:
#   python3 Инструменты/проверка_имён.py Нина Степан
import sys, glob, re
from публикации import готовые_публикации

files = glob.glob('Рассказ-*.md') + list(готовые_публикации('.', 'рассказ'))
def num(f):
    return int(re.match(r'(?:Рассказ|Публикация)-(\d+)', f).group(1))
last = sorted({num(f) for f in files})[-15:]
recent = [f for f in files if num(f) in last]
print('Последние рассказы:', ', '.join(map(str, last)))
for name in sys.argv[1:]:
    pat = r'(?<![А-Яа-яЁё])' + re.escape(name)
    hits = sorted({num(f) for f in recent if re.search(pat, open(f, encoding='utf-8').read())})
    if hits:
        print(f'{name}: есть в рассказах {", ".join(map(str, hits))}. Для героини и обидчика взять другое, второстепенному можно')
    else:
        print(f'{name}: можно')
