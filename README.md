# article-spoiler

Substack の記事 HTML ファイルを Markdown に変換する CLI ツール。

ブラウザの「名前を付けて保存」で保存した HTML ファイル（および付随する `_files/` ディレクトリ）を `input/` に置いて実行すると、`output/` に Markdown ファイルと画像が出力されます。

---

## 必要環境

- Python 3.14 以上
- [uv](https://docs.astral.sh/uv/)

---

## セットアップ

```bash
uv sync
```

---

## 使い方

### 1. 記事 HTML を input/ に配置

ブラウザで Substack 記事を開き、**「名前を付けて保存」→「ウェブページ、完全」** で保存します。
保存すると HTML ファイルと `<ファイル名>_files/` ディレクトリが生成されるので、両方を `input/` に置きます。

```
input/
├── My Article.html
└── My Article_files/
    ├── image1.jpg
    └── ...
```

### 2. 実行

```bash
uv run article-spoiler
```

オプションでディレクトリを指定することもできます。

```bash
uv run article-spoiler --input path/to/input --output path/to/output
```

### 3. 出力確認

```
output/
└── my-article/
    ├── my-article.md
    └── images/
        ├── image1.jpg
        └── ...
```

記事タイトルをスラッグ化したディレクトリが作成され、その中に Markdown ファイルと画像が格納されます。

---

## 備考

- 既に出力済みの記事はスキップされます（再実行しても上書きされません）。
- 対応する `_files/` ディレクトリが存在しない HTML はスキップされます。
