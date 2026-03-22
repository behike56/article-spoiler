import argparse
from pathlib import Path

from article_spoiler.extract import process_html


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Substack HTML articles to Markdown."
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
