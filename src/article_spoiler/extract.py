"""Extract article text from Substack HTML files as Markdown with images."""

import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

SKIP_TAGS = {"button", "svg", "picture", "source", "style", "script"}
TEXT_TAGS = {"p", "h2", "h3", "blockquote"}
INLINE_TAGS = {"em", "strong", "span", "a"}

IMAGES_DIR_NAME = "images"


class ArticleExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_body_markup = False
        self.body_markup_depth = 0
        self.skip_depth = 0
        self.elements: list[str] = []

        # Title/subtitle state (outside body markup)
        self.title: str = ""
        self.subtitle: str = ""
        self.in_title_h1 = False
        self.in_subtitle_h3 = False

        # Text collection state
        self.text_tag_stack: list[str] = []
        self.current_text: list[str] = []

        # List state
        self.in_ul = False
        self.in_li = False

        # Figure/image state
        self.in_figure = False
        self.current_img_src: str | None = None
        self.current_img_alt: str | None = None

        # Collected image filenames (source _files dir -> filename)
        self.image_filenames: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class") or ""

        # Title: <h1 class="post-title ...">
        if tag == "h1" and "post-title" in cls:
            self.in_title_h1 = True
            self.current_text = []
            return

        # Subtitle: <h3 class="subtitle ...">
        if tag == "h3" and "subtitle" in cls:
            self.in_subtitle_h3 = True
            self.current_text = []
            return

        if tag == "div":
            if "body markup" in cls:
                self.in_body_markup = True
                self.body_markup_depth = 1
                return
            if self.in_body_markup:
                self.body_markup_depth += 1

        if not self.in_body_markup:
            return

        if self.in_figure:
            if tag == "img":
                attrs_dict = dict(attrs)
                src = attrs_dict.get("src", "")
                alt = attrs_dict.get("alt", "")
                if src:
                    filename = src.rsplit("/", 1)[-1]
                    self.current_img_src = filename
                    self.current_img_alt = alt or ""
            return

        if self.skip_depth > 0:
            self.skip_depth += 1
            return

        if tag in SKIP_TAGS:
            self.skip_depth = 1
            return

        if tag == "figure":
            self.in_figure = True
            self.current_img_src = None
            self.current_img_alt = None
            return

        if tag == "ul":
            self.in_ul = True
            return

        if tag == "li":
            self.in_li = True
            return

        if tag in TEXT_TAGS:
            self.text_tag_stack.append(tag)
            self.current_text = []
            return

        if self.text_tag_stack and tag in INLINE_TAGS:
            if tag == "em":
                self.current_text.append("*")
            elif tag == "strong":
                self.current_text.append("**")

    def handle_endtag(self, tag: str) -> None:
        if self.in_title_h1 and tag == "h1":
            self.title = " ".join("".join(self.current_text).split())
            self.current_text = []
            self.in_title_h1 = False
            return

        if self.in_subtitle_h3 and tag == "h3":
            self.subtitle = " ".join("".join(self.current_text).split())
            self.current_text = []
            self.in_subtitle_h3 = False
            return

        if not self.in_body_markup:
            return

        if self.skip_depth > 0:
            self.skip_depth -= 1
            return

        if tag == "div":
            self.body_markup_depth -= 1
            if self.body_markup_depth <= 0:
                self.in_body_markup = False
            return

        if tag == "figure":
            if self.current_img_src:
                self.image_filenames.append(self.current_img_src)
                md_path = f"{IMAGES_DIR_NAME}/{self.current_img_src}"
                self.elements.append(f"![{self.current_img_alt or ''}]({md_path})")
            self.in_figure = False
            self.current_img_src = None
            self.current_img_alt = None
            return

        if tag == "ul":
            self.in_ul = False
            return

        if tag == "li":
            self.in_li = False
            return

        if self.text_tag_stack and tag in INLINE_TAGS:
            if tag == "em":
                self.current_text.append("*")
            elif tag == "strong":
                self.current_text.append("**")
            return

        if self.text_tag_stack and tag == self.text_tag_stack[-1]:
            self.text_tag_stack.pop()
            if not self.text_tag_stack:
                text = " ".join("".join(self.current_text).split())
                if text:
                    self._emit(tag, text)
                self.current_text = []

    def _emit(self, tag: str, text: str) -> None:
        if tag == "h2":
            self.elements.append(f"## {text}")
        elif tag == "h3":
            self.elements.append(f"### {text}")
        elif tag == "blockquote":
            self.elements.append(f"> {text}")
        elif tag == "p" and self.in_li:
            self.elements.append(f"- {text}")
        else:
            self.elements.append(text)

    def handle_data(self, data: str) -> None:
        if self.in_title_h1 or self.in_subtitle_h3:
            self.current_text.append(data)
            return
        if not self.in_body_markup or self.skip_depth > 0 or self.in_figure:
            return
        if self.text_tag_stack:
            self.current_text.append(data)


def title_to_dirname(title: str) -> str:
    """Convert a title like 'Earn *And* Learn' to 'earn-and-learn'."""
    name = title.lower()
    name = re.sub(r"[*_`~\[\]()]", "", name)  # strip Markdown punctuation
    name = re.sub(r"[^\w\s-]", "", name)       # strip remaining non-word chars
    name = re.sub(r"[\s_]+", "-", name).strip("-")
    return name


def process_html(html_path: Path, output_base: Path) -> None:
    """Process a single HTML file and produce a Markdown folder with images."""
    files_dir = html_path.with_name(html_path.stem + "_files")
    if not files_dir.is_dir():
        print(f"Skipped {html_path.name}: no corresponding _files directory")
        return

    html = html_path.read_text(encoding="utf-8")
    parser = ArticleExtractor()
    parser.feed(html)

    if not parser.title:
        print(f"Skipped {html_path.name}: no title found")
        return

    # Build Markdown content
    header: list[str] = [f"# {parser.title}"]
    if parser.subtitle:
        header.append(parser.subtitle)
    md = "\n\n".join(header + parser.elements) + "\n"

    # Create output directory: <output_base>/<title-slug>/
    slug = title_to_dirname(parser.title)
    out_dir = output_base / slug
    md_file = out_dir / f"{slug}.md"

    if md_file.exists():
        print(f"Skipped {html_path.name}: already processed ({md_file})")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Write Markdown
    md_file.write_text(md, encoding="utf-8")

    # Copy referenced images
    if parser.image_filenames:
        images_dir = out_dir / IMAGES_DIR_NAME
        images_dir.mkdir(exist_ok=True)
        for filename in parser.image_filenames:
            src = files_dir / filename
            if src.exists():
                shutil.copy2(src, images_dir / filename)
            else:
                print(f"  Warning: image not found: {src}")

    print(f"Wrote {md_file} ({len(parser.image_filenames)} images)")
