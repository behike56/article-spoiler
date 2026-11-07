import argparse
import sys
from pathlib import Path

from article_spoiler.extract import process_html


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "import":
        from article_spoiler.archive import archive_main

        archive_main(sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1] in {"auth", "fetch"}:
        from article_spoiler.remote import remote_main

        remote_main(sys.argv[1:])
        return
    parser = argparse.ArgumentParser(
        description="Extract Substack HTML articles to Markdown.",
        epilog="Commands: import ARCHIVE.zip, auth login, fetch URL. Run each command with --help for options.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("input"),
        help="Directory containing HTML files (default: input/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Directory for Markdown output (default: output/)",
    )
    args = parser.parse_args()

    html_files = sorted(args.input.glob("*.html"))
    if not html_files:
        print(f"No HTML files found in {args.input}")
        return
    for html_path in html_files:
        process_html(html_path, args.output)
