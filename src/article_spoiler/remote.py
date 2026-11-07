"""Interactive retrieval of articles using a dedicated browser profile."""

import argparse
import hashlib
import ipaddress
import mimetypes
import os
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from article_spoiler.extract import ArticleExtractor, title_to_dirname

PROFILE = Path.home() / ".local" / "share" / "article-spoiler" / "browser-profile"
MAX_IMAGE = 20 * 1024 * 1024


def validate_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("Only HTTPS URLs without credentials are supported")
    addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("URL resolves to a non-public address")


def remote_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Retrieve a subscribed article")
    commands = parser.add_subparsers(dest="command", required=True)
    auth = commands.add_parser("auth")
    auth.add_argument("action", choices=["login"])
    auth.add_argument("--profile-dir", type=Path, default=PROFILE)
    fetch = commands.add_parser("fetch")
    fetch.add_argument("url")
    fetch.add_argument("--output", type=Path, default=Path("output"))
    fetch.add_argument("--profile-dir", type=Path, default=PROFILE)
    args = parser.parse_args(argv)

    try:
        args.profile_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        os.chmod(args.profile_dir, 0o700)
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(str(args.profile_dir), headless=False)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                if args.command == "auth":
                    page.goto("https://substack.com/sign-in", wait_until="domcontentloaded")
                    input("Sign in in the browser, then press Enter here to finish: ")
                    return
                validate_url(args.url)
                page.goto(args.url, wait_until="domcontentloaded")
                validate_url(page.url)
                answer = input("Check that the complete article is visible in the browser. Save it? [y/N] ")
                if answer.strip().lower() not in {"y", "yes"}:
                    raise ValueError("Article was not confirmed; nothing was saved")
                save_article(page, context, args.output)
            finally:
                context.close()
    except (ValueError, OSError, PlaywrightError, EOFError) as exc:
        parser.exit(1, f"Error: {exc}\n")


def save_article(page, context, output: Path) -> None:
    result = page.evaluate("""() => {
      const title = document.querySelector('h1.post-title');
      const body = document.querySelector('div.body.markup');
      if (!title || !body || !body.innerText.trim()) return null;
      const clone = body.cloneNode(true);
      const originals = body.querySelectorAll('figure img');
      const images = [];
      clone.querySelectorAll('figure img').forEach((img, i) => {
        const url = originals[i].currentSrc || originals[i].src;
        const name = `image-${i + 1}`;
        images.push({url, name}); img.setAttribute('src', name);
      });
      const subtitle = document.querySelector('h3.subtitle');
      return {html: title.outerHTML + (subtitle ? subtitle.outerHTML : '') + clone.outerHTML, images};
    }""")
    if not result:
        raise ValueError("Article title or body was not found; page structure may have changed")
    article = ArticleExtractor()
    article.feed(result["html"])
    if not article.title or not article.elements:
        raise ValueError("Article could not be extracted")
    slug = title_to_dirname(article.title) or "article"
    key = hashlib.sha256(page.url.encode()).hexdigest()[:12]
    output.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = output / f"{slug}-{key}"
    if target.exists():
        print(f"Skipped: {target} already exists")
        return
    with tempfile.TemporaryDirectory(dir=output, prefix=".article-") as temp:
        staging = Path(temp)
        if result["images"]:
            (staging / "images").mkdir(mode=0o700)
        for image in result["images"]:
            validate_url(image["url"])
            response = context.request.get(image["url"], max_redirects=0, timeout=30000)
            if not response.ok or not response.headers.get("content-type", "").startswith("image/"):
                raise ValueError("Image download failed or returned a non-image response")
            if int(response.headers.get("content-length", "0")) > MAX_IMAGE:
                raise ValueError("Image exceeds size limit")
            content = response.body()
            if len(content) > MAX_IMAGE:
                raise ValueError("Image exceeds size limit")
            content_type = response.headers["content-type"].split(";", 1)[0].lower()
            extension = mimetypes.guess_extension(content_type) or ""
            filename = image["name"] + extension
            (staging / "images" / filename).write_bytes(content)
            article.elements = [element.replace(f"](images/{image['name']})", f"](images/{filename})") for element in article.elements]
        header = [f"# {article.title}"]
        if article.subtitle:
            header.append(article.subtitle)
        (staging / f"{slug}.md").write_text("\n\n".join(header + article.elements) + "\n", encoding="utf-8")
        os.rename(staging, target)
    print(f"Wrote {target}")
