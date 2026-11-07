import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from article_spoiler.archive import import_archive


class ArchiveTests(unittest.TestCase):
    def write_archive(self, root, **changes):
        data = {
            "version": 1, "url": "https://example.com/p/article?tracking=1",
            "full_text_confirmed": True,
            "html": '<h1 class="post-title">Article</h1><div class="body markup"><p>Paid text</p><figure><img src="asset-1.png" alt="Chart"></figure></div>',
            "images": [{"name": "asset-1.png", "path": "images/asset-1.png"}],
        }
        data.update(changes)
        source = root / "article.zip"
        with ZipFile(source, "w") as archive:
            archive.writestr("article.json", json.dumps(data))
            archive.writestr("images/asset-1.png", b"png")
        return source

    def test_import_images_and_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.write_archive(root)
            result = import_archive(source, root / "output")
            self.assertIn("Paid text", (result / "article.md").read_text())
            self.assertIn("images/asset-1.png", (result / "article.md").read_text())
            self.assertEqual((result / "images/asset-1.png").read_bytes(), b"png")
            self.assertEqual(import_archive(source, root / "output"), result)
            self.assertEqual(len(list((root / "output").iterdir())), 1)

    def test_reject_unconfirmed_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.write_archive(root, full_text_confirmed=False)
            with self.assertRaises(ValueError):
                import_archive(source, root / "output")
            self.assertFalse((root / "output").exists())

    def test_reject_traversal_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.write_archive(root, images=[{"name": "../escape.png", "path": "../escape.png"}])
            with self.assertRaises(ValueError):
                import_archive(source, root / "output")
            self.assertFalse((root / "output").exists())

    def test_missing_image_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.write_archive(root, images=[{"name": "asset-2.png", "path": "images/asset-2.png"}])
            with self.assertRaises(KeyError):
                import_archive(source, root / "output")
            self.assertFalse((root / "output").exists())
