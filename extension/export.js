const status = document.querySelector('#status');
const save = document.querySelector('#save');
const confirmed = document.querySelector('#confirmed');
const id = new URLSearchParams(location.search).get('id');
let article;
const MAX_IMAGE = 20 * 1024 * 1024;
const MAX_TOTAL = 100 * 1024 * 1024;
function imageUrl(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password) throw new Error('HTTPS 以外の画像には対応していません。');
  return url;
}
async function waitForDownload(downloadId) {
  const deadline = Date.now() + 10 * 60 * 1000;
  while (Date.now() < deadline) {
    const [item] = await chrome.downloads.search({id: downloadId});
    if (!item) throw new Error('ダウンロード情報が見つかりません。Chrome のダウンロード履歴を確認してください。');
    if (item.state === 'complete') return item.filename;
    if (item.state === 'interrupted') throw new Error(`ダウンロードが中断されました（${item.error || '原因不明'}）。再度保存してください。`);
    await new Promise(resolve => setTimeout(resolve, 300));
  }
  throw new Error('保存完了を確認できませんでした。Chrome のダウンロード履歴を確認してください。');
}
(async () => {
  article = (await chrome.storage.session.get(id))[id];
  if (!article || article.error) throw new Error(article?.error || '記事データがありません。元のタブで再実行してください。');
  document.querySelector('#title').textContent = `${article.title}（画像 ${article.images.length} 件）`;
  confirmed.addEventListener('change', () => {save.disabled = !confirmed.checked;});
})().catch(error => {status.textContent = error.message;});
save.addEventListener('click', async () => {
  save.disabled = true;
  try {
    if (article.images.length > 1000) throw new Error('画像が1000件を超える記事には対応していません。');
    const origins = [...new Set(article.images.map(image => imageUrl(image.url).origin + '/*'))];
    if (origins.length && !(await chrome.permissions.request({origins}))) throw new Error('画像の取得権限が許可されませんでした。');
    const files = [], images = [];
    let total = 0, html = article.html;
    for (const image of article.images) {
      status.textContent = `画像を取得中 ${images.length + 1}/${article.images.length}`;
      const response = await fetch(imageUrl(image.url), {credentials: 'omit', redirect: 'error', signal: AbortSignal.timeout(30000)});
      const mime = (response.headers.get('content-type') || '').split(';')[0].toLowerCase();
      const extensions = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif', 'image/avif': '.avif', 'image/svg+xml': '.svg'};
      if (!response.ok || !extensions[mime]) throw new Error('画像を取得できないか、未対応の画像形式です。ZIP は保存していません。');
      const reader = response.body.getReader();
      const parts = []; let size = 0;
      try {
        while (true) {
          const {done, value} = await reader.read(); if (done) break;
          size += value.length; total += value.length;
          if (size > MAX_IMAGE || total > MAX_TOTAL) throw new Error('画像のサイズ上限を超えました。');
          parts.push(value);
        }
      } finally {await reader.cancel();}
      const data = new Uint8Array(size); let offset = 0;
      for (const part of parts) {data.set(part, offset); offset += part.length;}
      const name = image.name + extensions[mime];
      html = html.replace(`src="${image.name}"`, `src="${name}"`);
      images.push({name, path: `images/${name}`}); files.push({name: `images/${name}`, data});
    }
    const manifest = {version: 1, url: article.url, html, images, full_text_confirmed: true};
    const manifestBytes = new TextEncoder().encode(JSON.stringify(manifest));
    if (manifestBytes.length > 5 * 1024 * 1024) throw new Error('本文のサイズ上限を超えました。');
    files.push({name: 'article.json', data: manifestBytes});
    const url = URL.createObjectURL(createZip(files));
    let filename;
    try {
      const downloadId = await chrome.downloads.download({url, filename: 'article-spoiler.zip', saveAs: true});
      status.textContent = '保存完了を確認しています。このタブを閉じずにお待ちください。';
      filename = await waitForDownload(downloadId);
    } finally {URL.revokeObjectURL(url);}
    await chrome.storage.session.remove(id);
    const quotedPath = "'" + filename.replaceAll("'", "'\\''") + "'";
    status.textContent = `保存が完了しました。\n保存先: ${filename}\n\n次のコマンドで変換してください:\nuv run article-spoiler import ${quotedPath}`;
  } catch (error) {
    status.textContent = `保存できませんでした: ${error.message}`;
    save.disabled = !confirmed.checked;
  }
});
