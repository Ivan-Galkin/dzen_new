import sqlite3
import unicodedata
from datetime import datetime, timezone


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


class Journal:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS publications(
              channel TEXT, number TEXT, kind TEXT, path TEXT, title TEXT, digest TEXT,
              status TEXT, draft_url TEXT, uploaded_at TEXT, error TEXT,
              PRIMARY KEY(channel, number));
            CREATE TABLE IF NOT EXISTS remote(
              channel TEXT, remote_id TEXT, title TEXT, status TEXT, url TEXT,
              PRIMARY KEY(channel, remote_id));
            CREATE TABLE IF NOT EXISTS baselines(channel TEXT PRIMARY KEY);
        """)

    def observe(self, channel, item, article, relpath):
        with self.db:
            self.db.execute("""INSERT OR IGNORE INTO publications
                VALUES(?,?,?,?,?,?,'review',NULL,NULL,NULL)""",
                (channel, item.number, item.kind, relpath, article.title, article.digest))
            self.db.execute("""UPDATE publications SET path=?, title=?, digest=?, kind=?, status='review'
                WHERE channel=? AND number=? AND status IN ('review','approved') AND digest<>?""",
                (relpath, article.title, article.digest, item.kind, channel, item.number, article.digest))
        return self.row(channel, item.number)

    def row(self, channel, number):
        return self.db.execute("SELECT * FROM publications WHERE channel=? AND number=?",
                               (channel, number)).fetchone()

    def reconcile(self, channel, inventory):
        """Call only with a verified complete inventory of this exact channel."""
        with self.db:
            self.db.execute("DELETE FROM remote WHERE channel=?", (channel,))
            titles = {}
            for entry in inventory:
                if entry["status"] not in ("draft", "scheduled", "published") or not entry["id"]:
                    raise ValueError("Неполная карточка Студии")
                self.db.execute("INSERT INTO remote VALUES(?,?,?,?,?)",
                                (channel, entry["id"], entry["title"], entry["status"], entry.get("url")))
                titles.setdefault(normalize(entry["title"]), []).append(entry)
            for row in self.db.execute("SELECT * FROM publications WHERE channel=?", (channel,)):
                matches = titles.get(normalize(row["title"]), [])
                if matches and row["status"] != "verified":
                    # Even one title match prevents creation. An interrupted write still
                    # needs a body/status check to qualify as a verified upload.
                    if row["status"] == "pending":
                        continue
                    state = "matched" if len(matches) == 1 else "review"
                    self.db.execute("UPDATE publications SET status=?,draft_url=? WHERE channel=? AND number=?",
                                    (state, matches[0].get("url") if len(matches)==1 else None, channel, row["number"]))
            self.db.execute("INSERT OR IGNORE INTO baselines VALUES(?)", (channel,))

    def reserve(self, channel, number, digest):
        with self.db:
            cur = self.db.execute("""UPDATE publications SET status='pending' WHERE channel=? AND number=?
                AND digest=? AND status='approved' AND EXISTS(SELECT 1 FROM baselines WHERE channel=?)""",
                (channel, number, digest, channel))
            if cur.rowcount != 1:
                raise ValueError("Нет подтверждённого допуска к созданию черновика")

    def verified(self, channel, number, url):
        with self.db:
            cur = self.db.execute("""UPDATE publications SET status='verified',draft_url=?,uploaded_at=?,
                error=NULL WHERE channel=? AND number=? AND status='pending'""",
                (url, datetime.now(timezone.utc).isoformat(), channel, number))
            if cur.rowcount != 1:
                raise ValueError("Нет зарезервированной операции")
