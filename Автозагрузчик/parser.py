import re
from dataclasses import dataclass
from hashlib import sha256

PHOTO = re.compile(r"(?:\*\*)?\[ФОТО\s*(\d*)(?:\s*[-—–.:][^\]]*)?\](?:\*\*)?$", re.I)
INLINE = re.compile(r"\[Задание на картинку:\s*(.+)\]$", re.I)
FENCE = re.compile(r"^(\x60{3,}|~{3,})(.*)$")
PLACEHOLDER = re.compile(r"\[[^]\n]*(?:ссылк|вставить|ник(?: канала)?|заглушк)[^]\n]*\](?!\()|\]\((?:#|TODO|URL)?\)|\{\{[^}]+\}\}", re.I)


@dataclass
class Article:
    title: str
    body: str
    images: list
    warnings: list

    @property
    def digest(self):
        return sha256((self.title + "\n" + self.body).encode()).hexdigest()

    def html(self):
        import markdown2
        return str(markdown2.markdown(self.body, safe_mode="escape",
                                      extras=["tables", "fenced-code-blocks", "break-on-newline"]))


def parse(raw):
    boundary = re.search(r"(?m)^(?:={5,}\n)?(?:## )?НИЖЕ В ПУБЛИКАЦИЮ НЕ ИДЁТ\b", raw)
    appendix = raw[boundary.start():] if boundary else ""
    lines = (raw[:boundary.start()] if boundary else raw).lstrip("\ufeff").strip().splitlines()
    if not lines:
        raise ValueError("Пустой файл")
    title = re.sub(r"^#\s+", "", lines.pop(0)).strip()
    if title.startswith("**") and title.endswith("**"):
        title = title[2:-2]
    if title in ("", "---") or title.startswith(("<!--", "[")):
        raise ValueError("Проверьте заголовок и метаданные")
    body, images = [], []
    i = 0
    fence = None

    def nonblank(index):
        while index < len(lines) and not lines[index].strip():
            index += 1
        return index

    while i < len(lines):
        line = lines[i].strip()
        photo = PHOTO.fullmatch(line)
        inline = INLINE.fullmatch(line)
        cover = line.startswith("**Обложка.**")
        if fence or not (photo or inline or cover):
            marker = FENCE.match(line)
            if fence and re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + ",}", line):
                fence = None
            elif marker and not fence:
                fence = marker[1]
            elif not fence and re.search(r"^\W*(?:ФОТО\s*\d|Промп?т\s*:|Обложка\s*[:.]|Задание на картинку:)|^!\[|^<!--", line, re.I):
                raise ValueError(f"Неопознанный служебный блок, строка {i+2}")
            body.append(lines[i])
            i += 1
            continue
        previous = "\n".join(body).strip().split("\n\n")[-1] or "После заголовка"
        image = dict(number=int(photo[1]) if photo and photo[1] else len(images)+1,
                     marker=line, after=previous, prompt=inline[1] if inline else "", caption="")
        i += 1
        j = nonblank(i)
        if not inline and j < len(lines) and (marker := FENCE.match(lines[j].strip())):
            end = j + 1
            while end < len(lines) and lines[end].strip() != marker[1]:
                end += 1
            if end == len(lines):
                raise ValueError("Незакрытый блок промпта")
            image["prompt"] = "\n".join(lines[j+1:end])
            i = end + 1
        elif photo and "подлинное" in line.casefold() and j < len(lines) and re.match(r"(?:Ссылка: *)?https://", lines[j]):
            image["source"] = lines[j].strip()
            i = j + 1
            if i < len(lines) and lines[i].strip():
                image["caption"] = lines[i]
                i += 1
        elif not inline and (cover or "пром" in line.casefold()):
            raise ValueError("Метка изображения без распознанного промпта")
        j = nonblank(i)
        if j < len(lines) and re.fullmatch(r"(?:Подпись:\s*.+|Изображение создано ИИ[.]?)", lines[j], re.I):
            image["caption"] = lines[j].removeprefix("Подпись:").strip()
            i = j + 1
        j = nonblank(i)
        if j < len(lines) and lines[j] == "Вариант для проверки фотореалистичного стиля:":
            start = nonblank(j + 1)
            if start >= len(lines) or lines[start].strip() != chr(96)*3:
                raise ValueError("Проверьте альтернативный промпт")
            end = lines.index(chr(96)*3, start+1)
            image["alternative_prompt"] = "\n".join(lines[start+1:end])
            i = end+1
        images.append(image)
    if fence:
        raise ValueError("Незакрытый блок кода")
    if appendix:
        sections = re.split(r"(?m)^--- ФОТО (\d+)[^\n]*---\s*$", appendix)
        prompts = dict(zip(sections[1::2], sections[2::2]))
        for image in images:
            section = prompts.get(str(image["number"]), "").strip()
            if section:
                image["prompt"] = re.split(r"\n\s*\n", section, maxsplit=1)[0]
            elif image["number"] == 1:
                cover = re.search(r"### Промт для обложки\s+\x60{3}\n(.*?)\n\x60{3}", appendix, re.S)
                if cover:
                    image["prompt"] = cover[1]
        # Historical appendices also contain provenance and alternative pictures.
        if images:
            images[0]["source_notes"] = appendix
    content = "\n".join(body).strip()
    if not content:
        raise ValueError("Нет основного текста")
    return Article(title, content, images, PLACEHOLDER.findall(content))
