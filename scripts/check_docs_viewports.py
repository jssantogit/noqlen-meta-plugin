#!/usr/bin/env python3
"""Smoke-test built Material for MkDocs at desktop and mobile viewports.

Runs only against a locally generated site/ tree. It never contacts remote
docs and never modifies a live library, server, or release.
"""

from __future__ import annotations

import argparse
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGES = (
    ("/", "Noqlen Meta", "home"),
    ("/start-here/quickstart/", "Quickstart: preview one album", "quickstart"),
    ("/start-here/installation/", "Install Noqlen Meta", "installation"),
    ("/start-here/reading-preview/", "Read your first preview", "preview"),
    ("/recipes/combine-features/", "Combine features", "combined-config"),
)
VIEWPORTS = {"desktop": (1366, 900), "mobile": (390, 844)}
MAX_DOCUMENT_OVERFLOW = 8


def check_site(site: Path, artifacts: Path) -> list[dict[str, object]]:
    if not (site / "index.html").is_file():
        raise RuntimeError(f"Missing built site/index.html in {site}")
    artifacts.mkdir(parents=True, exist_ok=True)
    handler = partial(SimpleHTTPRequestHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    observed: list[dict[str, object]] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome", headless=True, args=["--no-sandbox"]
            )
            try:
                for name, (width, height) in VIEWPORTS.items():
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=1,
                        is_mobile=name == "mobile",
                        has_touch=name == "mobile",
                    )
                    try:
                        for route, heading, slug in PAGES:
                            page = context.new_page()
                            try:
                                response = page.goto(origin + route, wait_until="networkidle")
                                assert response and response.status == 200, (
                                    name, route, response.status if response else None
                                )
                                page.wait_for_selector(".md-content h1")
                                title = page.locator(".md-content h1").first.inner_text()
                                assert heading.lower() in title.lower(), (
                                    name, route, heading, title
                                )
                                assert page.locator(".md-header").is_visible(), (name, route)
                                assert page.locator(".md-content").is_visible(), (name, route)
                                overflow = page.evaluate(
                                    "() => document.documentElement.scrollWidth - window.innerWidth"
                                )
                                assert overflow <= MAX_DOCUMENT_OVERFLOW, (
                                    "horizontal overflow", name, route, overflow
                                )
                                if slug == "home":
                                    cards = page.locator(".md-typeset .grid.cards > ul > li")
                                    if cards.count() == 0:
                                        cards = page.locator(".md-typeset .grid.cards > li")
                                    assert cards.count() >= 4, (
                                        name, "homepage cards missing", cards.count()
                                    )
                                    bounds = [cards.nth(i).bounding_box() for i in range(4)]
                                    assert all(b is not None for b in bounds)
                                    first_x = [round(b["x"]) for b in bounds if b]
                                    # On mobile the responsive Material cards should form one column.
                                    if name == "mobile":
                                        assert len(set(first_x)) == 1, (
                                            "mobile cards are not a single column", first_x
                                        )
                                    else:
                                        assert len(set(first_x)) > 1, (
                                            "desktop cards did not form a grid", first_x
                                        )
                                if slug == "installation":
                                    labels = " ".join(
                                        page.locator(".tabbed-labels > label").all_text_contents()
                                    ).lower()
                                    assert "pipx" in labels and "uv tool" in labels, (
                                        name, "installation tabs absent", labels
                                    )
                                shot = artifacts / f"{name}-{slug}.png"
                                page.screenshot(path=str(shot), full_page=True)
                                observed.append(
                                    {
                                        "viewport": name,
                                        "route": route,
                                        "heading": title,
                                        "horizontal_overflow_px": overflow,
                                        "screenshot": str(shot),
                                    }
                                )
                            finally:
                                page.close()
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    return observed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path("docs-responsive-screenshots"),
    )
    args = parser.parse_args()
    results = check_site(args.site.resolve(), args.artifacts.resolve())
    print(json.dumps(results, indent=2))
    print(f"PASS: {len(results)} real-browser responsive documentation checks")
