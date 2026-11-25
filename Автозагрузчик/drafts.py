"""Protocol shared by the pilot and future Studio UI adapter. No DOM selectors here."""
from collections import Counter
from difflib import SequenceMatcher

from storage import normalize


def prepare(journal, channel, entries, observed, inventory, approvals=()):
    """Entries are scanned before the initial complete inventory. Approval includes the digest.
    observed is the set of numbers already in SQLite before this scan.
    inventory must include all three lists, fully paginated and channel-verified.
    """
    had_baseline = journal.db.execute("SELECT 1 FROM baselines WHERE channel=?", (channel,)).fetchone()
    journal.reconcile(channel, inventory)
    remote = [normalize(entry["title"]) for entry in inventory]
    counts = Counter(normalize(article.title) for item, article in entries)
    for item, article in entries:
        row = journal.row(channel, item.number)
        title = normalize(article.title)
        # All previously reserved, matched or verified identities stay suppressed.
        if row["status"] not in ("review", "approved"):
            continue
        decision = (item.number, article.digest) in approvals
        similar = any(SequenceMatcher(None, title, other).ratio() >= .84 for other in remote)
        new = bool(had_baseline and item.number not in observed)
        safe = (not item.hold and not item.recorded and counts[title] == 1 and title not in remote
                and row["digest"] == article.digest and (not item.title or normalize(item.title) == title))
        prior = journal.db.execute("""SELECT 1 FROM publications WHERE channel=? AND number<>?
            AND (digest=? OR path=? OR title=?) AND status IN ('verified','matched','pending')""",
            (channel, item.number, article.digest, row["path"], article.title)).fetchone()
        eligible = safe and not prior and (decision or (not similar and (new or row["status"] == "approved")))
        with journal.db:
            journal.db.execute("UPDATE publications SET status=? WHERE channel=? AND number=?",
                               ("approved" if eligible else "review", channel, item.number))


def create_one(studio, journal, channel, item, article):
    """No automatic retry after reserve. Existing items have no edit path."""
    studio.require_channel(channel)
    if journal.db.execute("SELECT 1 FROM publications WHERE channel=? AND status='pending'",
                          (channel,)).fetchone():
        raise ValueError("Сначала проверьте незавершённый черновик этого канала")
    journal.reserve(channel, item.number, article.digest)
    try:
        draft = studio.create_empty_draft()
        # Persist a reference before inserting text so a crash can be investigated.
        with journal.db:
            journal.db.execute("UPDATE publications SET draft_url=? WHERE channel=? AND number=?",
                               (draft, channel, item.number))
        studio.require_empty_draft(channel, draft)
        studio.fill_title_and_html(article.title, article.html())
        studio.wait_saved()
        studio.reopen_and_verify(channel, draft, article)
        journal.verified(channel, item.number, draft)
    except Exception as exc:
        with journal.db:
            journal.db.execute("UPDATE publications SET error=? WHERE channel=? AND number=?",
                               (str(exc), channel, item.number))
        raise
