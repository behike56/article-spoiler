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

URL から記事を取得する場合は、ブラウザもインストールします。

```bash
uv run playwright install chromium
```

## ログイン済みの Chrome タブから取得

普段の Chrome に拡張機能を追加すると、その Chrome で閲覧できる記事を取得できます。

1. Chrome で `chrome://extensions` を開き、「デベロッパー モード」を有効にします。
2. 「パッケージ化されていない拡張機能を読み込む」で、このリポジトリの `extension/` フォルダを選びます。
3. Substack の記事を開いて末尾まで読み込み、ツールバーの拡張機能一覧から「Article Spoiler」を押します。
4. 開いた保存画面で全文を確認したチェックを入れ、「記事と画像を ZIP に保存」を押します。画像配信元へのアクセス許可が表示されたら確認してください。
5. 保存画面の「保存が完了しました」を確認し、そこに表示される実際の保存先を使ったコマンドで変換します。以下は標準の保存先を選んだ場合の例です。

```bash
uv run article-spoiler import ~/Downloads/article-spoiler.zip
```

`--output path/to/output` で出力先を変更できます。ZIP には記事の内容が含まれるため、変換後に不要になった ZIP は削除してください。保存画面はダウンロードが完了するまで開いたままにしてください。

画像のアクセス拒否、リダイレクト、認証が必要な画像、未対応形式の場合は ZIP の作成を中止します。PNG、JPEG、WebP、GIF、AVIF、SVG に対応し、画像は1件20 MiB、合計100 MiBまでです。本文が全文かどうかは自動判定しないため、プレビューを保存しないよう利用者自身で確認してください。

## 専用ブラウザで URL から取得

専用ブラウザで Substack にログインします。ログイン後、ターミナルで Enter を押します。

```bash
uv run article-spoiler auth login
```

記事 URL を指定し、開いたブラウザで記事の全文が表示されていることを確認してから、ターミナルで `y` を入力します。

```bash
uv run article-spoiler fetch 'https://example.substack.com/p/article-slug'
```

認証状態は `~/.local/share/article-spoiler/browser-profile` に保存されます。セッションが期限切れになった場合は再ログインしてください。画像を取得できない場合は記事全体の保存を中止します。表示内容や記事の末尾は利用者自身で確認してください。

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

### 4. エージェントに日本語訳を依頼

出力された Markdown の日本語訳は、Codex などのエージェントに依頼します。依頼時には、翻訳対象の `output/` と配置先の `jpn_article/` を指定してください。

依頼例：

> `output/` の Markdown を日本語に翻訳し、`jpn_article/` に配置してください。見出し・リンク・コードを保ち、画像もコピーして、翻訳先から参照できるようにしてください。

---

## 備考

- 既に出力済みの記事はスキップされます（再実行しても上書きされません）。
- 対応する `_files/` ディレクトリが存在しない HTML はスキップされます。

今後の RSS 対応などは、[有料テキスト記事の取得設計](docs/paid-article-ingestion-design.md)にまとめています。

## 開発時の確認

```bash
uv run python -m unittest discover -s tests -v
PYTHONPATH=src uv run python tests/browser_extension_smoke.py
```

後者はテスト用 Chromium と一時プロファイルを使い、ZIP のダウンロードから変換まで確認します。記事・画像の応答、画像配信元の許可、保存先の選択をテスト用に置き換えており、購読中の実記事や Chrome の許可ダイアログの検証は含みません。
