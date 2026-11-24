"""Take screenshots of the running project for the README / portfolio.

Requires the stack to be running with seed data:
    docker compose up -d && docker compose exec api python -m app.seed

Note: the Mailpit screenshot places a real order (as the demo customer).

Usage:
    pip install playwright && playwright install chromium
    python scripts/take_screenshots.py
"""

import html
import os
import subprocess
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
MAILPIT_URL = os.getenv("MAILPIT_URL", "http://localhost:8025")
EMAIL = os.getenv("DEMO_EMAIL", "ana.petrovic@example.com")
PASSWORD = os.getenv("DEMO_PASSWORD", "password123")
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "screenshots"

# 1000x750 CSS pixels at 2x scale -> 2000x1500 images with large, crisp text.
VIEWPORT = {"width": 1000, "height": 750}
SCALE = 2

TAGS = ["Auth", "Authors", "Books", "Categories", "Customers", "Orders"]


def open_docs(page: Page) -> None:
    page.goto(f"{BASE_URL}/docs")
    page.wait_for_selector(".opblock-tag-section.is-open")


def settle(page: Page, scroll_y: float = 0) -> None:
    """Move the mouse out of the way (no hover styles) and scroll."""
    page.mouse.move(0, 0)
    page.evaluate("y => window.scrollTo(0, y)", scroll_y)
    page.wait_for_timeout(300)


def swagger_overview(page: Page) -> None:
    """Top of the page: title, Authorize button and the Auth/Authors/Books tags.

    Only Auth stays expanded so that the tags below it fit in the frame.
    """
    open_docs(page)
    for tag in TAGS[1:]:
        page.click(f"#operations-tag-{tag}")
    settle(page)
    page.screenshot(path=OUT_DIR / "swagger-overview.png")


def authorize(page: Page) -> None:
    """Log in through Swagger's Authorize dialog (OAuth2 password flow)."""
    page.click(".auth-wrapper button.authorize")
    page.fill("#oauth_username", EMAIL)
    page.fill("#oauth_password", PASSWORD)
    page.click(".auth-btn-wrapper button.authorize")
    page.wait_for_selector(".auth-btn-wrapper button:has-text('Logout')")
    page.click(".auth-btn-wrapper button.btn-done")


def swagger_get_books(page: Page) -> None:
    """GET /books after Execute, scrolled to the server response (200 + body)."""
    open_docs(page)
    authorize(page)

    operation = page.locator("#operations-Books-list_books_books_get")
    operation.locator(".opblock-summary").click()
    operation.locator("button.try-out__btn").click()
    operation.locator("button.execute").click()
    heading = operation.locator("h4:has-text('Server response')")
    heading.wait_for()

    # "Server response" at the top hides the curl command and request URL above.
    top = heading.evaluate("el => el.getBoundingClientRect().top + window.scrollY")
    settle(page, top - 8)
    page.screenshot(path=OUT_DIR / "swagger-get-books.png")


def mailpit_order_email(page: Page) -> None:
    """Place an order through the API and open its confirmation email in Mailpit.

    The email is sent by the Celery worker, so this also shows the worker works.
    """
    token = page.request.post(
        f"{BASE_URL}/auth/login", form={"username": EMAIL, "password": PASSWORD}
    ).json()["access_token"]
    response = page.request.post(
        f"{BASE_URL}/orders",
        headers={"Authorization": f"Bearer {token}"},
        data={"items": [{"book_id": 5, "quantity": 1}, {"book_id": 9, "quantity": 2}]},
    )
    assert response.ok, response.text()
    subject = f"Order #{response.json()['id']} confirmed"

    for _ in range(20):  # wait up to ~10 s for the worker to deliver the email
        messages = page.request.get(f"{MAILPIT_URL}/api/v1/messages").json()
        match = [m for m in messages["messages"] if m["Subject"] == subject]
        if match:
            break
        page.wait_for_timeout(500)
    else:
        raise RuntimeError(f"Email '{subject}' did not arrive in Mailpit")

    page.goto(f"{MAILPIT_URL}/view/{match[0]['ID']}")
    page.frame_locator("iframe").get_by_text("Thank you for your order!").wait_for()
    settle(page)
    page.screenshot(path=OUT_DIR / "mailpit-order-email.png")


PS_COMMAND = [
    "docker",
    "compose",
    "ps",
    "--format",
    "table {{.Service}}\t{{.Image}}\t{{.Status}}",
]

TERMINAL_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  html, body {{ margin: 0; height: 100%; background: #0c0c0c; }}
  .window {{ height: 100%; display: flex; flex-direction: column; }}
  .titlebar {{ background: #2b2b2b; color: #ccc; padding: 10px 16px;
              font: 14px "Segoe UI", sans-serif; }}
  .screen {{ flex: 1; display: flex; align-items: center; justify-content: center; }}
  pre {{ margin: 0; color: #cccccc;
        font: 18px/1.6 "Cascadia Mono", Consolas, monospace; }}
  .prompt {{ color: #6ab0f3; }}
</style></head><body><div class="window">
  <div class="titlebar">Terminal: bookstore-api</div>
  <div class="screen"><pre><span class="prompt">$</span> {command}

{output}</pre></div>
</div></body></html>"""


def docker_compose_ps(page: Page) -> None:
    """Real `docker compose ps` output, rendered as a terminal window."""
    output = subprocess.run(
        PS_COMMAND, cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout
    # Shown exactly as typed, with a literal \t.
    command = (
        r"docker compose ps --format " r'"table {{.Service}}\t{{.Image}}\t{{.Status}}"'
    )
    page.set_content(
        TERMINAL_HTML.format(
            command=html.escape(command), output=html.escape(output.rstrip())
        )
    )
    page.screenshot(path=OUT_DIR / "docker-compose-ps.png")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for shot in (
            swagger_overview,
            swagger_get_books,
            mailpit_order_email,
            docker_compose_ps,
        ):
            page = browser.new_page(viewport=VIEWPORT, device_scale_factor=SCALE)
            shot(page)
            page.close()
        browser.close()
    print(f"Screenshots saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
