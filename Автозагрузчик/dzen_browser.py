import re


def login(state, profile):
    """Only open Studio in an isolated visible profile. Owner handles login/checks."""
    from playwright.sync_api import sync_playwright
    if not re.fullmatch(r"[A-Za-z0-9_-]+", profile):
        raise ValueError("Недопустимое имя профиля")
    with sync_playwright() as browser:
        context = browser.chromium.launch_persistent_context(
            str(state / "profiles" / profile), headless=False,
            args=["--lang=ru-RU"], locale="ru-RU")
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://dzen.ru/profile/editor", wait_until="domcontentloaded", timeout=60000)
            input("Войдите в Студию в открытом окне. После входа нажмите Enter здесь. ")
        finally:
            context.close()
