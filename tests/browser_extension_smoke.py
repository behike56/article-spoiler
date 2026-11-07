import json
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
from article_spoiler.archive import import_archive

ROOT = Path.cwd()
with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    # Grant a fixture origin in this temporary test copy only.
    extension = temp / 'extension'
    extension.mkdir()
    for source in (ROOT / 'extension').iterdir():
        (extension / source.name).write_bytes(source.read_bytes())
    manifest = json.loads((extension / 'manifest.json').read_text())
    manifest['host_permissions'] = ['https://example.com/*']
    (extension / 'manifest.json').write_text(json.dumps(manifest))
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(temp / 'profile'), channel='chromium', headless=True, downloads_path=str(temp / 'downloads'),
            args=[f'--disable-extensions-except={extension}', f'--load-extension={extension}'])
        try:
            worker = context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
            context.route('https://example.com/**', lambda route: route.fulfill(content_type='text/html', body='<h1 class="post-title">Fixture</h1><div class="body markup"><p>Complete fixture text</p><figure><img src="https://example.com/image.png"></figure></div>'))
            context.route('https://example.com/image.png', lambda route: route.fulfill(content_type='image/png', body=b'png'))
            page = context.new_page()
            page.goto('https://example.com/p/article')
            with context.expect_page() as opened:
                worker.evaluate('''async () => {const [tab] = await chrome.tabs.query({url: 'https://example.com/p/article'}); await captureTab(tab);}''')
            exporter = opened.value
            exporter.wait_for_selector('#title:text("Fixture")')
            exporter.evaluate("""() => {
              const download = chrome.downloads.download.bind(chrome.downloads);
              chrome.downloads.download = options => download({...options, saveAs: false});
            }""")
            exporter.check('#confirmed')
            exporter.click('#save')
            exporter.wait_for_function("() => document.querySelector('#status').textContent.startsWith('保存が完了しました。')")
            filename = exporter.evaluate("async () => (await chrome.downloads.search({limit: 1, orderBy: ['-startTime']}))[0].filename")
            archive = Path(filename)
            assert archive.is_file()
            result = import_archive(archive, temp / 'output')
            assert 'Complete fixture text' in (result / 'fixture.md').read_text()
            assert not exporter.locator('#status').inner_text().startswith('保存できませんでした')
            print('Chromium extension capture -> ZIP -> Python Markdown import OK')
        finally:
            context.close()
