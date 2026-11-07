// Only the tab on which the user invokes the action is inspected.
async function captureTab(tab) {
  const id = crypto.randomUUID();
  try {
    if (!tab.id || !tab.url?.startsWith('https://')) throw new Error('HTTPS の記事タブで実行してください。');
    const [{result}] = await chrome.scripting.executeScript({
      target: {tabId: tab.id},
      func: () => {
        const title = document.querySelector('h1.post-title');
        const body = document.querySelector('div.body.markup');
        if (!title || !body || !body.innerText.trim()) throw new Error('記事のタイトルまたは本文が見つかりません。');
        const clone = body.cloneNode(true);
        const originals = body.querySelectorAll('img');
        const images = [];
        clone.querySelectorAll('img').forEach((image, i) => {
          const url = originals[i].currentSrc || originals[i].src;
          const name = `asset-${i + 1}`;
          images.push({url, name});
          image.setAttribute('src', name);
          image.removeAttribute('srcset');
        });
        // Scripts and embedded active content are not part of the archive.
        clone.querySelectorAll('script, iframe, object, embed, style').forEach(el => el.remove());
        const subtitle = document.querySelector('h3.subtitle');
        return {version: 1, url: location.origin + location.pathname, title: title.innerText,
          html: title.outerHTML + (subtitle?.outerHTML || '') + clone.outerHTML, images};
      }
    });
    await chrome.storage.session.set({[id]: result});
  } catch (error) {
    await chrome.storage.session.set({[id]: {error: error.message}});
  }
  await chrome.tabs.create({url: chrome.runtime.getURL(`export.html?id=${id}`)});
}
chrome.action.onClicked.addListener(captureTab);
