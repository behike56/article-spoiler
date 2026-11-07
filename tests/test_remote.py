import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from article_spoiler.remote import save_article, validate_url


class Page:
    url = "https://example.com/p/article"

    def evaluate(self, script):
        return {"html": '<h1 class="post-title">Example</h1><div class="body markup"><p>Body</p><figure><img src="image-1"></figure></div>', "images": [{"url": "https://example.com/image", "name": "image-1"}]}


class Response:
    ok = True
    headers = {"content-type": "image/png"}

    def body(self):
        return b"image"


class Request:
    def get(self, *args, **kwargs):
        return Response()


class Context:
    request = Request()


class RemoteTests(unittest.TestCase):
    def test_rejects_non_https(self):
        with self.assertRaises(ValueError):
            validate_url("http://localhost/article")

    @patch("article_spoiler.remote.validate_url")
    def test_save_and_skip_existing(self, validate):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            save_article(Page(), Context(), output)
            directory = next(output.iterdir())
            markdown = next(directory.glob("*.md")).read_text()
            self.assertIn("Body", markdown)
            self.assertIn("images/image-1.png", markdown)
            self.assertEqual((directory / "images/image-1.png").read_bytes(), b"image")
            save_article(Page(), Context(), output)
            self.assertEqual(len(list(output.iterdir())), 1)

    @patch("article_spoiler.remote.validate_url")
    def test_failed_image_leaves_no_article(self, validate):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(Request, "get", side_effect=ValueError("failed")):
                with self.assertRaises(ValueError):
                    save_article(Page(), Context(), Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
