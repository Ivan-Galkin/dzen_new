"""Файлы с едиными номерами по «ВЫКЛАДКЕ» канала."""

from pathlib import Path


def готовые_публикации(папка, формат=None):
    папка = Path(папка)
    таблица = папка / 'ВЫКЛАДКА.md'
    if not таблица.is_file():
        return
    for строка in таблица.read_text(encoding='utf-8-sig').splitlines():
        if not строка.startswith('|'):
            continue
        поля = [поле.strip() for поле in строка.strip().strip('|').split('|')]
        if len(поля) != 6 or not поля[0].isdigit():
            continue
        номер, вид, статус, _, _, имя = поля
        if статус.casefold() != 'готово' or (формат is not None and вид.casefold() != формат):
            continue
        if имя == f'Публикация-{int(номер):02d}_ГОТОВО-К-ВСТАВКЕ.md':
            путь = папка / имя
            if путь.is_file():
                yield str(путь)
