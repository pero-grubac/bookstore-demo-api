"""Record a ~45 s demo video of the running project (Swagger -> order -> email).

Steps: Authorize in Swagger, GET /books, POST /orders with two books, then open
the confirmation email in Mailpit. The result is screenshots/demo.mp4 (H.264).

Requires the stack to be running with seed data, plus ffmpeg on PATH:
    docker compose up -d && docker compose exec api python -m app.seed
    python scripts/record_demo.py

Note: this places a real order as the demo customer.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
MAILPIT_URL = os.getenv("MAILPIT_URL", "http://localhost:8025")
EMAIL = os.getenv("DEMO_EMAIL", "ana.petrovic@example.com")
PASSWORD = os.getenv("DEMO_PASSWORD", "password123")
OUTPUT = Path(__file__).resolve().parent.parent / "screenshots" / "demo.mp4"
SIZE = {"width": 1280, "height": 720}

ORDER_BODY = {"items": [{"book_id": 3, "quantity": 1}, {"book_id": 7, "quantity": 1}]}

# Headless recordings have no mouse pointer, so draw one that follows the mouse.
CURSOR_JS = """
window.addEventListener("DOMContentLoaded", () => {
  const dot = document.createElement("div");
  Object.assign(dot.style, {
    position: "fixed", left: "-40px", top: "-40px", width: "20px", height: "20px",
    borderRadius: "50%", background: "rgba(239, 68, 68, .6)",
    border: "2px solid white", boxShadow: "0 0 6px rgba(0, 0, 0, .5)",
    transform: "translate(-50%, -50%)", transition: "transform .12s",
    pointerEvents: "none", zIndex: 2147483647,
  });
  document.body.appendChild(dot);
  const scale = (s) => (dot.style.transform = `translate(-50%, -50%) scale(${s})`);
  document.addEventListener("mousemove", (e) => {
    dot.style.left = e.clientX + "px";
    dot.style.top = e.clientY + "px";
  }, true);
  document.addEventListener("mousedown", () => scale(1.7), true);
  document.addEventListener("mouseup", () => scale(1), true);
});
"""


def pause(page: Page, seconds: float = 1.5) -> None:
    page.wait_for_timeout(seconds * 1000)


def click(page: Page, target: Locator) -> None:
    """Glide the mouse to the element before clicking, so viewers can follow."""
    target.scroll_into_view_if_needed()
    box = target.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=25)
    pause(page, 0.3)
    target.click()


def scroll_to(page: Page, target: Locator, offset: int = 80) -> None:
    top = target.evaluate("el => el.getBoundingClientRect().top + window.scrollY")
    page.evaluate("y => window.scrollTo({top: y, behavior: 'smooth'})", top - offset)
    pause(page, 1)


def authorize(page: Page) -> None:
    click(page, page.locator(".auth-wrapper button.authorize"))
    pause(page, 0.8)
    page.locator("#oauth_username").press_sequentially(EMAIL, delay=40)
    page.locator("#oauth_password").press_sequentially(PASSWORD, delay=40)
    pause(page, 0.5)
    click(page, page.locator(".auth-btn-wrapper button.authorize"))
    page.wait_for_selector(".auth-btn-wrapper button:has-text('Logout')")
    pause(page, 1.2)
    click(page, page.locator(".auth-btn-wrapper button.btn-done"))
    pause(page)


def get_books(page: Page) -> None:
    operation = page.locator("#operations-Books-list_books_books_get")
    click(page, operation.locator(".opblock-summary"))
    pause(page, 1)
    click(page, operation.locator("button.try-out__btn"))
    pause(page, 0.8)
    click(page, operation.locator("button.execute"))
    response = operation.locator("h4:has-text('Server response')")
    response.wait_for()
    scroll_to(page, response)
    pause(page, 3.5)
    # Collapse it again so the page stays short.
    click(page, operation.locator(".opblock-summary"))
    pause(page)


def create_order(page: Page) -> int:
    operation = page.locator("#operations-Orders-create_order_orders_post")
    click(page, operation.locator(".opblock-summary"))
    pause(page, 1)
    click(page, operation.locator("button.try-out__btn"))
    pause(page, 0.8)
    body = operation.locator("textarea.body-param__text")
    body.fill(json.dumps(ORDER_BODY, indent=2))
    pause(page, 2)
    with page.expect_response(
        lambda r: r.request.method == "POST" and r.url.endswith("/orders")
    ) as info:
        click(page, operation.locator("button.execute"))
    assert info.value.status == 201, info.value.text()
    response = operation.locator("h4:has-text('Server response')")
    response.wait_for()
    scroll_to(page, response)
    pause(page, 4)
    return info.value.json()["id"]


def open_email(page: Page, order_id: int) -> None:
    page.goto(MAILPIT_URL)
    message = page.get_by_text(f"Order #{order_id} confirmed").first
    message.wait_for(timeout=15_000)
    pause(page, 2.5)
    click(page, message)
    page.frame_locator("iframe").get_by_text("Thank you for your order!").wait_for()
    pause(page, 5)


def record(video_dir: Path) -> Path:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport=SIZE, record_video_dir=video_dir, record_video_size=SIZE
        )
        context.add_init_script(CURSOR_JS)
        page = context.new_page()

        page.goto(f"{BASE_URL}/docs")
        page.wait_for_selector(".opblock-tag-section.is-open")
        pause(page, 2.5)
        authorize(page)
        get_books(page)
        order_id = create_order(page)
        open_email(page, order_id)

        context.close()  # finishes writing the video
        browser.close()
        return Path(page.video.path())


def to_mp4(webm: Path, mp4: Path) -> None:
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    command = [ffmpeg, "-y", "-loglevel", "error", "-i", str(webm)]
    command += ["-c:v", "libx264", "-preset", "slow", "-crf", "20"]
    command += ["-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(mp4)]
    subprocess.run(command, check=True)


def to_gif(mp4: Path, gif: Path) -> None:
    """GIF for the README (GitHub does not play repository videos inline)."""
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    filters = (
        "fps=10,scale=960:-1:flags=lanczos,split[a][b];"
        "[a]palettegen=max_colors=128:stats_mode=diff[p];"
        "[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
    )
    command = [ffmpeg, "-y", "-loglevel", "error", "-i", str(mp4)]
    command += ["-vf", filters, "-loop", "0", str(gif)]
    subprocess.run(command, check=True)


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        webm = record(Path(tmp))
        to_mp4(webm, OUTPUT)
    to_gif(OUTPUT, OUTPUT.with_suffix(".gif"))
    print(f"Demo video saved to {OUTPUT} and {OUTPUT.with_suffix('.gif')}")


if __name__ == "__main__":
    main()
