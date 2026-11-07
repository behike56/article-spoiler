"""Import the versioned archive produced by the Chrome extension."""

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile

from article_spoiler.extract import ArticleExtractor, title_to_dirname

MAX_TOTAL = 110 * 1024 * 1024


def import_archive(source: Path, output: Path) -> Path:
    with ZipFile(source) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or len(names) > 1001:
            raise ValueError("Invalid or duplicate archive entries")
        if sum(entry.file_size for entry in entries) > MAX_TOTAL:
            raise ValueError("Archive exceeds size limit")
        if "article.json" not in names or archive.getinfo("article.json").file_size > 5 * 1024 * 1024:
            raise ValueError("Missing or oversized article manifest")
        data = json.loads(archive.read("article.json"))
        if not isinstance(data, dict) or data.get("version") != 1 or data.get("full_text_confirmed") is not True:
            raise ValueError("Unsupported or unconfirmed article archive")
        url, html, images = data.get("url"), data.get("html"), data.get("images")
        if not isinstance(url, str) or not isinstance(html, str) or not isinstance(images, list):
            raise ValueError("Invalid article manifest")
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("Invalid article URL")
        assets = {}
        for image in images:
            if not isinstance(image, dict) or not isinstance(image.get("name"), str):
                raise ValueError("Invalid image manifest")
            name = image["name"]
            if not re.fullmatch(r"asset-[1-9][0-9]*\.(jpg|png|webp|gif|avif|svg)", name):
                raise ValueError("Invalid image name")
            if image.get("path") != f"images/{name}" or name in assets:
                raise ValueError("Invalid or duplicate image path")
            if archive.getinfo(image["path"]).file_size > 20 * 1024 * 1024:
                raise ValueError("Image exceeds size limit")
            assets[name] = archive.read(image["path"])
        if set(names) != {"article.json", *(f"images/{name}" for name in assets)}:
            raise ValueError("Unexpected archive entries")
        article = ArticleExtractor()
        article.feed(html)
        if not article.title or not article.elements:
            raise ValueError("Article title or body was not found")
        if not set(article.image_filenames).issubset(assets):
            raise ValueError("An article image is missing")
        canonical = f"https://{parts.netloc.lower()}{parts.path}"
        key = hashlib.sha256(canonical.encode()).hexdigest()[:12]
        slug = (title_to_dirname(article.title) or "article")[:100]
        output.mkdir(parents=True, mode=0o700, exist_ok=True)
        target = output / f"{slug}-{key}"
        if target.exists():
            return target
        with tempfile.TemporaryDirectory(dir=output, prefix=".article-") as temp:
            staging = Path(temp)
            if assets:
                (staging / "images").mkdir(mode=0o700)
            for name, content in assets.items():
                (staging / "images" / name).write_bytes(content)
            header = [f"# {article.title}"]
            if article.subtitle:
                header.append(article.subtitle)
            (staging / f"{slug}.md").write_text("\n\n".join(header + article.elements) + "\n", encoding="utf-8")
            os.rename(staging, target)
        return target


def archive_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Import an Article Spoiler extension ZIP")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args(argv)
    try:
        target = import_archive(args.archive, args.output)
    except FileNotFoundError:
        parser.exit(1, f"Error: ZIP が見つかりません: {args.archive}\n拡張機能で ZIP の保存を完了し、保存画面に表示された実際のパスを指定してください。\n")
    except (ValueError, OSError, BadZipFile, KeyError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Article available at {target}")
