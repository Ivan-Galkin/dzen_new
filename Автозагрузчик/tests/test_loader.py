import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from drafts import create_one, prepare
from main import lock
from parser import parse
from scanner import Item, scan
from storage import Journal


class Formatting(unittest.TestCase):
    def test_author_markup_and_prompts(self):
        code = chr(96)*3
        original = ("# Тема\n\n**Жирный** и *курсив*. [Ссылка](https://example.org).\n\n"
                    + r"\*\*\*" + "\n\n**[ФОТО 2 — сгенерировать. Промт ниже]**\n"
                    + code + "\nprivate prompt\n" + code + "\nПодпись: Изображение создано ИИ\n\n"
                    + "> Цитата\n\n- пункт\n\n" + code + "\n[ФОТО 3]\n" + code
                    + "\n\n| А | Б |\n|---|---|\n| 1 | 2 |\n\nСпасибо! [вставить ссылку]")
        a = parse(original)
        html = a.html()
        for expected in ("<strong>", "<em>", "<table>", "<blockquote>", "<li>", "<code>",
                         "***", "https://example.org", "[ФОТО 3]", "Спасибо!"):
            self.assertIn(expected, html)
        self.assertNotIn("private prompt", html)
        self.assertEqual(a.images[0]["prompt"], "private prompt")
        self.assertEqual(a.images[0]["after"], r"\*\*\*")
        self.assertTrue(a.warnings)

    def test_unclosed_prompt(self):
        with self.assertRaises(ValueError):
            parse("Имя\n\n[ФОТО 1]\n" + chr(96)*3 + "\nчасть")


class Safety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.db = Journal(self.path / "state.db")
        self.addCleanup(self.db.db.close)
        self.item = Item("57", "рассказ", Path("источник.md"))
        self.article = parse("Свечницу лишили месячины\n\nТекст.")
        self.entries = [(self.item, self.article)]
        self.db.observe("barskaya", self.item, self.article, "источник.md")
        self.studio = Mock()
        self.studio.create_empty_draft.return_value = "draft-57"

    def prepare(self, inventory=(), approved=False):
        approvals = [("57", self.article.digest)] if approved else []
        prepare(self.db, "barskaya", self.entries, {"57"}, inventory, approvals)

    def test_first_scan(self):
        self.prepare()
        with self.assertRaises(ValueError):
            create_one(self.studio, self.db, "barskaya", self.item, self.article)
        self.studio.create_empty_draft.assert_not_called()

    def test_all_inventory_states(self):
        for status in ("draft", "scheduled", "published"):
            self.prepare([dict(title=self.article.title, id="123", status=status)], True)
            self.assertEqual(self.db.row("barskaya", "57")["status"], "matched")

    def test_crash_after_creation(self):
        self.prepare(approved=True)
        self.studio.wait_saved.side_effect = RuntimeError("не подтверждено")
        with self.assertRaises(RuntimeError):
            create_one(self.studio, self.db, "barskaya", self.item, self.article)
        with self.assertRaises(ValueError):
            self.prepare(approved=True)
            create_one(self.studio, self.db, "barskaya", self.item, self.article)
        self.studio.create_empty_draft.assert_called_once()
        self.assertEqual(self.db.row("barskaya", "57")["status"], "pending")

    def test_verified_survives_rename(self):
        self.prepare(approved=True)
        create_one(self.studio, self.db, "barskaya", self.item, self.article)
        other = parse("Новое имя\n\nИсправленный текст")
        self.db.observe("barskaya", self.item, other, "другой.md")
        with self.assertRaises(ValueError):
            create_one(self.studio, self.db, "barskaya", self.item, other)
        self.assertEqual(self.db.row("barskaya", "57")["draft_url"], "draft-57")
        self.studio.create_empty_draft.assert_called_once()

    def test_wrong_channel(self):
        self.prepare(approved=True)
        self.studio.require_channel.side_effect = ValueError("канал")
        with self.assertRaises(ValueError):
            create_one(self.studio, self.db, "barskaya", self.item, self.article)
        self.studio.create_empty_draft.assert_not_called()

    def test_exclusive_lock(self):
        with lock(self.path):
            with self.assertRaises(RuntimeError), lock(self.path):
                self.fail()
        with lock(self.path):
            pass


class RepositoryFormats(unittest.TestCase):
    def test_aygul_numbering_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / "ВЫКЛАДКА.md"
            legacy = [
                f"| {n} | рассказ {n:02d} | готово | | Заголовок | Рассказ-{n:02d}_ГОТОВО-К-ВСТАВКЕ.md |"
                for n in range(1, 45) if n != 42
            ]
            legacy.insert(41, "| 42 | рецепт 11 | резерв снят | | | (не написано) |")
            future = [
                "| 45 | рецепт | готово | | Рецепт | Рассказ-45.md |",
                "| 46 | кухни мира | готово | | История блюда | Рассказ-46.md |",
                "| 47 | рассказ | в очереди | | | (не написано) |",
                "| 48 | рассказ | готово | | Рассказ | Рассказ-48.md |",
            ]
            channel = {"folder": ".", "source": "queue"}
            queue.write_text("\n".join(legacy + future), encoding="utf-8")
            items = scan(root, channel)
            self.assertEqual([x.number for x in items[-4:]], ["43", "44", "45", "46"])
            self.assertEqual(items[-2].path.name, "Рассказ-45.md")
            self.assertEqual([x.kind for x in items[-2:]], ["рецепт", "кухни"])

            future[0] = future[0].replace("Рассказ-45.md", "Рассказ-46.md")
            queue.write_text("\n".join(legacy + future), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Неизвестный файл публикации 45"):
                scan(root, channel)

    def test_channels_from_actual_repository(self):
        module = Path(__file__).resolve().parents[1]
        root = Path(os.environ.get("DZEN_TEST_SOURCE", module.parent))
        channels = json.loads((module / "config.example.json").read_text(encoding="utf-8"))["channels"]
        for channel in channels:
            with self.subTest(channel=channel["name"]):
                items = scan(root, channel)
                self.assertTrue(items)
                for item in items:
                    article = parse(item.path.read_text(encoding="utf-8-sig"))
                    self.assertTrue(article.body)
                    self.assertNotRegex(article.body, r"(?im)^\W*\[ФОТО|НИЖЕ В ПУБЛИКАЦИЮ НЕ ИДЁТ|wide 16:9 aspect ratio")
                if channel["source"] == "queue":
                    self.assertEqual(items[5].path.name, "Рецепт-01_ГОТОВО-К-ВСТАВКЕ.md")
                    self.assertEqual(items[11].kind, "кухни")
                    self.assertFalse(any(x.path.name.startswith("Рассказ-02_") for x in items))
                if channel["source"] == "marketing":
                    self.assertTrue(items[0].hold)
                if channel["id"] == "barskaya":
                    sample = next(x for x in items if x.number == "57")
                    a = parse(sample.path.read_text(encoding="utf-8-sig"))
                    self.assertEqual(a.title, "Свечницу лишили месячины")
                    self.assertIn("Спасибо, что дочитали", a.body)
                    self.assertTrue(all(im["prompt"] for im in a.images))
