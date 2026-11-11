
#!/usr/bin/env python3
"""Playwright tests for LilBit BigLife at 390px and 1280px."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SHOTS = Path("/workspace/lilbit-biglife/shots")
SHOTS.mkdir(parents=True, exist_ok=True)
CHROME = "/usr/bin/google-chrome"
VIEWPORTS = {"390": {"width": 390, "height": 844}, "1280": {"width": 1280, "height": 800}}


def overflow(page):
    return page.evaluate(
        """() => {
          const doc = document.documentElement;
          const body = document.body;
          return {
            scrollWidth: Math.max(doc.scrollWidth, body.scrollWidth),
            clientWidth: doc.clientWidth,
            overflowing: Math.max(doc.scrollWidth, body.scrollWidth) > doc.clientWidth + 1
          };
        }"""
    )


def shot(page, name):
    path = SHOTS / name
    page.screenshot(path=str(path), full_page=True)
    return path


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    errs = []
    failures = []

    def record_console(msg):
        if msg.type == "error":
            errs.append(f"console.error: {msg.text}")

    def record_pageerror(exc):
        errs.append(f"pageerror: {exc}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport=VIEWPORTS["390"],
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        page.on("console", record_console)
        page.on("pageerror", record_pageerror)
        page.on("dialog", lambda d: d.accept())

        page.goto(url, wait_until="networkidle")
        page.wait_for_selector('[data-testid="privacy-note"]')

        # Privacy and personalization
        privacy = page.locator('[data-testid="privacy-note"]').inner_text()
        if "Saved only on this phone. Nothing is shared unless you share it." not in privacy:
            failures.append("missing privacy sentence")
        title = page.locator("h1.brand-title").inner_text()
        subtitle = page.locator(".brand-for").inner_text()
        if title.strip() != "LilBit BigLife":
            failures.append(f"unexpected title: {title!r}")
        if "LillyClaire" not in subtitle:
            failures.append("title should say for LillyClaire")
        if "LillyClaire" not in page.locator('[data-testid="welcome"]').inner_text():
            failures.append("welcome should greet LillyClaire")
        safety = page.locator('[data-testid="safety-note"]').inner_text()
        if "988" not in safety or "parent" not in safety.lower():
            failures.append("missing safety note")

        shot(page, "friends-empty-390.png")

        # Empty trends
        page.locator('[data-testid="tab-trends"]').click()
        page.wait_for_selector('[data-testid="trends-empty"]')
        if "LillyClaire" not in page.locator('[data-testid="encouragement"]').inner_text():
            failures.append("empty trends should speak to LillyClaire")
        shot(page, "trends-empty-390.png")
        page.locator('[data-testid="tab-friends"]').click()

        # Load example friends
        page.locator('[data-testid="btn-load-examples"]').click()
        page.wait_for_selector('[data-testid="friend-card"]')
        cards = page.locator('[data-testid="friend-card"]')
        names = [cards.nth(i).locator("h3").inner_text() for i in range(cards.count())]
        if names != ["Maya", "Jordan", "Priya"]:
            failures.append(f"example friends unexpected: {names}")
        if cards.count() != 3:
            failures.append(f"expected 3 example friends, got {cards.count()}")
        if "Example (fictional)" not in cards.nth(0).inner_text():
            failures.append("examples should be marked fictional")
        shot(page, "examples-390.png")

        # Example trends data
        page.locator('[data-testid="tab-trends"]').click()
        page.wait_for_selector('[data-testid="trends-chart"]')
        total = int(page.locator('[data-testid="stat-total"]').inner_text())
        worry = int(page.locator('[data-testid="stat-worry"]').inner_text())
        hurt = int(page.locator('[data-testid="stat-hurt"]').inner_text())
        right = int(page.locator('[data-testid="stat-right"]').inner_text())
        if total != 10 or worry != 8 or hurt != 1 or right != 1:
            failures.append(f"example trends mismatch: total={total} worry={worry} hurt={hurt} right={right}")
        enc = page.locator('[data-testid="encouragement"]').inner_text()
        if "LillyClaire, 8 of 10 worries were just worry" not in enc:
            failures.append(f"encouragement unexpected: {enc}")
        if "wildly good even though imperfect" not in enc:
            failures.append("missing wildly good line")
        if page.locator('[data-testid="history-item"]').count() != 10:
            failures.append("expected 10 example history items")
        page.locator('[data-testid="chart-range-monthly"]').click()
        page.wait_for_selector('[data-testid="trends-chart"]')
        shot(page, "trends-examples-390.png")

        # Remove examples
        page.locator('[data-testid="tab-friends"]').click()
        page.locator('[data-testid="btn-remove-examples"]').click()
        page.wait_for_selector('[data-testid="friends-empty"]')
        page.locator('[data-testid="tab-trends"]').click()
        page.wait_for_selector('[data-testid="trends-empty"]')
        page.locator('[data-testid="tab-friends"]').click()

        # Add a friend with 5 items (what she told me)
        page.locator('[data-testid="btn-add-friend"]').click()
        page.wait_for_selector('[data-testid="input-friend-name"]')
        # Ask-your-friend prompt path is also exercised
        page.locator('[data-testid="btn-method-ask"]').click()
        page.wait_for_selector('[data-testid="share-prompt"]')
        prompt = page.locator('[data-testid="share-prompt"]').inner_text()
        if "5 things" not in prompt:
            failures.append("ask prompt should request 5 things")
        page.locator('[data-testid="btn-method-told"]').click()
        page.fill('[data-testid="input-friend-name"]', "Avery")
        items = [
            "Leaving me out of plans",
            "Sharing a secret I trusted you with",
            "Cancelling on me a lot",
            "Joking about something I'm sensitive about",
            "Not checking in when I'm having a hard time",
        ]
        for i, text in enumerate(items):
            page.fill(f'[data-testid="item-input-{i}"]', text)
        shot(page, "add-friend-390.png")
        page.locator('[data-testid="btn-save-friend"]').click()
        page.wait_for_selector('[data-testid="friend-card"]')
        if page.locator('[data-testid="friend-card"] h3').inner_text() != "Avery":
            failures.append("saved friend name missing")
        if "What she told me" not in page.locator('[data-testid="friend-card"]').inner_text():
            failures.append("source label missing")

        # Worried -> did-one path
        page.locator('[data-testid="tab-worried"]').click()
        page.wait_for_selector('[data-testid="select-friend"]')
        page.select_option('[data-testid="select-friend"]', label="Avery")
        page.fill('[data-testid="worry-note"]', "I think I cancelled plans.")
        shot(page, "worried-pick-390.png")
        page.locator('[data-testid="btn-start-checkin"]').click()
        page.wait_for_selector('[data-testid="item-check-0"]')
        page.locator('[data-testid="item-check-2"]').check()
        shot(page, "worried-items-390.png")
        page.locator('[data-testid="btn-continue-items"]').click()
        page.wait_for_selector('[data-testid="reconcile-view"]')
        apology = page.locator('[data-testid="apology-template"]').inner_text()
        if "I'm sorry I" not in apology or "I care about you and I'll" not in apology:
            failures.append(f"apology template unexpected: {apology}")
        if "one mistake" not in page.locator('[data-testid="reconcile-view"]').inner_text().lower():
            failures.append("reconcile should reassure one mistake doesn't define her")
        page.fill('[data-testid="note-to-self"]', "Text her tomorrow and apologize.")
        shot(page, "reconcile-390.png")
        page.locator('[data-testid="btn-save-reconcile"]').click()
        page.wait_for_selector('[data-testid="history-item"]')
        if "Real hurt" not in page.locator('[data-testid="history-item"]').first.inner_text():
            failures.append("real hurt history not saved")
        # Mark made it right
        page.locator('[data-testid="btn-made-right"]').first.click()
        page.wait_for_selector('text=Made it right')
        if int(page.locator('[data-testid="stat-right"]').inner_text()) < 1:
            failures.append("made it right did not update stats")

        # Worried -> none -> not sure -> yes -> affirmation
        page.locator('[data-testid="tab-worried"]').click()
        page.wait_for_selector('[data-testid="select-friend"]')
        page.select_option('[data-testid="select-friend"]', label="Avery")
        page.fill('[data-testid="worry-note"]', "I overthought a short text.")
        page.locator('[data-testid="btn-start-checkin"]').click()
        page.wait_for_selector('[data-testid="btn-none"]')
        page.locator('[data-testid="btn-none"]').check()
        page.locator('[data-testid="btn-continue-items"]').click()
        page.wait_for_selector('[data-testid="belief-view"]')
        q = page.locator('[data-testid="belief-question"]').inner_text()
        if "Avery" not in q or "told you the truth" not in q:
            failures.append(f"belief question unexpected: {q}")
        shot(page, "belief-390.png")
        page.locator('[data-testid="belief-unsure"]').click()
        page.wait_for_selector('[data-testid="unsure-view"]')
        if "assume the worst" not in page.locator('[data-testid="unsure-view"]').inner_text().lower():
            failures.append("unsure path should say not to assume the worst")
        shot(page, "unsure-390.png")
        page.locator('[data-testid="btn-believe-now"]').click()
        page.wait_for_selector('[data-testid="affirmation-view"]')
        aff = page.locator('[data-testid="affirmation-text"]').inner_text()
        if "LillyClaire" not in aff:
            failures.append(f"affirmation should name LillyClaire: {aff}")
        saying = page.locator('[data-testid="family-saying"]').inner_text()
        if "Be your own friend and fan" not in saying:
            failures.append(f"missing family saying: {saying}")
        shot(page, "affirmation-390.png")
        page.locator('[data-testid="btn-see-trends"]').click()
        page.wait_for_selector('[data-testid="history-item"]')
        hist_count = page.locator('[data-testid="history-item"]').count()
        if hist_count < 2:
            failures.append(f"expected at least 2 history items, got {hist_count}")
        shot(page, "trends-after-checkins-390.png")

        # Persistence after reload
        page.reload(wait_until="networkidle")
        page.wait_for_selector('[data-testid="friend-card"]')
        if page.locator('[data-testid="friend-card"] h3').inner_text() != "Avery":
            failures.append("friend did not persist after reload")
        page.locator('[data-testid="tab-trends"]').click()
        page.wait_for_selector('[data-testid="history-item"]')
        if page.locator('[data-testid="history-item"]').count() < 2:
            failures.append("history did not persist after reload")
        # overflow at 390
        ov = overflow(page)
        if ov["overflowing"]:
            failures.append(f"horizontal overflow at 390: {ov}")
        shot(page, "trends-390.png")

        # Desktop 1280
        page.set_viewport_size(VIEWPORTS["1280"])
        page.locator('[data-testid="tab-friends"]').click()
        page.wait_for_selector('[data-testid="friend-card"]')
        ov = overflow(page)
        if ov["overflowing"]:
            failures.append(f"horizontal overflow on friends at 1280: {ov}")
        shot(page, "friends-1280.png")
        page.locator('[data-testid="tab-trends"]').click()
        page.wait_for_selector('[data-testid="trends-chart"]')
        ov = overflow(page)
        if ov["overflowing"]:
            failures.append(f"horizontal overflow on trends at 1280: {ov}")
        shot(page, "trends-1280.png")
        page.locator('[data-testid="tab-worried"]').click()
        page.wait_for_selector('[data-testid="worried-pick"]')
        ov = overflow(page)
        if ov["overflowing"]:
            failures.append(f"horizontal overflow on worried at 1280: {ov}")
        shot(page, "worried-1280.png")

        # Also capture friends at 390 after data exists
        page.set_viewport_size(VIEWPORTS["390"])
        page.locator('[data-testid="tab-friends"]').click()
        page.wait_for_selector('[data-testid="friend-card"]')
        ov = overflow(page)
        if ov["overflowing"]:
            failures.append(f"horizontal overflow on friends at 390: {ov}")
        shot(page, "friends-390.png")

        browser.close()

    print("console/page errors:", len(errs))
    for e in errs:
        print(" ERR", e)
    print("failures:", len(failures))
    for f in failures:
        print(" FAIL", f)

    if errs:
        failures.append("console or page errors present")
    if failures:
        sys.exit(1)
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
