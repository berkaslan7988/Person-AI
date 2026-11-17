"""Regenerate the README screenshots (docs/screens/<name>-<theme>.png).

Needs Playwright (`pip install playwright && playwright install chromium`) and a server running on
a throwaway data folder, so no real chats end up in the pictures. On Windows:

    mkdir %TEMP%\\pai-shots
    type nul > %TEMP%\\pai-shots\\person_ai.db
    set PAI_FAKE=1& set PAI_DATA_DIR=%TEMP%\\pai-shots& set PAI_PORT=8572& set PAI_PUBLIC_HOST=
    python server.py --no-browser
    python tools/screenshots.py --base http://127.0.0.1:8572

The empty person_ai.db stops the first start from importing an older app's database.
"""

import argparse
import os
import secrets
from datetime import datetime, timedelta, timezone

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWPORT = {"width": 1440, "height": 900}  # wide enough for all four starter cards in one row
SCALE = 1.25

# A short scene with Haruki, the first starter character.
CHAT = [
    ("user", "*sets down a worn travel pack* Is it that obvious?"),
    ("assistant", "*a faint smile* Your boots told me. Your face only agreed. *slides a small plate of rice "
                  "crackers across the counter* Eat first. Then tell me which way you're headed. The pass gets "
                  "cold after dark."),
    ("user", "North. Toward the old monastery."),
    ("assistant", "*pauses mid-pour* ...Not many go that way anymore. *sets the kettle down slowly* Stay the "
                  "night. In the morning I'll draw you a map, and tell you which bridges still hold."),
]


def seed(request, base):
    """Create the demo account, switch it to English and add one chat with Haruki."""
    r = request.post(f"{base}/api/auth/register",
                     data={"username": "alex", "password": secrets.token_urlsafe(12)})
    if not r.ok:
        raise SystemExit(f"register failed: {r.status} {r.text()} (use a fresh data folder)")
    request.get(f"{base}/api/bootstrap")  # seeds the starter characters
    request.patch(f"{base}/api/settings", data={"language": "en", "onboarding_seen": "1", "user_name": "Alex"})
    chars = request.get(f"{base}/api/characters").json()["characters"]
    haruki = next(c for c in chars if c["name"] == "Haruki")
    t = datetime.now(timezone.utc) - timedelta(minutes=12)
    messages = [{"role": "assistant", "content": haruki["greeting"], "timestamp": t.isoformat(),
                 "swipes": [haruki["greeting"], *haruki["alt_greetings"]], "swipe": 0}]
    for i, (role, text) in enumerate(CHAT, 1):
        messages.append({"role": role, "content": text, "timestamp": (t + timedelta(minutes=2 * i)).isoformat()})
    session = request.post(f"{base}/api/sessions",
                           data={"character_id": haruki["id"], "messages": messages}).json()["session"]
    request.get(f"{base}/api/sessions/{session['id']}")  # make it the active chat


def shoot(page, out, name, theme):
    page.wait_for_timeout(1400)  # let entrance animations settle
    path = os.path.join(out, f"{name}-{theme}.png")
    page.screenshot(path=path)
    print("saved", os.path.relpath(path, ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8572")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "screens"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    base = args.base.rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        opts = {"viewport": VIEWPORT, "device_scale_factor": SCALE}

        setup = browser.new_context(**opts)
        seed(setup.request, base)
        state = setup.storage_state()
        setup.close()

        for theme in ("dark", "light"):
            prefs = f"try {{ localStorage.setItem('pai.theme', '{theme}'); localStorage.setItem('pai.lang', 'en') }} catch (e) {{}}"

            guest = browser.new_context(color_scheme=theme, **opts)
            guest.add_init_script(prefs)
            page = guest.new_page()
            page.goto(base)
            page.wait_for_selector(".lp-title")
            shoot(page, args.out, "landing", theme)
            guest.close()

            ctx = browser.new_context(color_scheme=theme, storage_state=state, **opts)
            ctx.add_init_script(prefs)
            ctx.request.patch(f"{base}/api/settings", data={"theme_mode": theme})
            page = ctx.new_page()
            page.goto(base)
            page.wait_for_selector(".thread")
            shoot(page, args.out, "chat", theme)

            page.get_by_text("Characters", exact=True).first.click()
            page.wait_for_selector(".grid")
            shoot(page, args.out, "characters", theme)

            page.get_by_text("Settings", exact=True).first.click()
            page.get_by_text("Appearance", exact=True).first.click()
            shoot(page, args.out, "settings", theme)
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
