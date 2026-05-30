chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'saveMarkdown') {
    handleSaveMarkdown(request.tabId).then(sendResponse).catch(err => {
      sendResponse({ success: false, error: err.message });
    });
    return true;
  }
});

async function handleSaveMarkdown(tabId) {
  try {
    let response = null;
    try {
      response = await chrome.tabs.sendMessage(tabId, { action: 'getMarkdown' });
    } catch (msgErr) {
      if (msgErr.message.includes('Receiving end does not exist') ||
          msgErr.message.includes('Could not establish connection')) {
        await chrome.scripting.executeScript({
          target: { tabId: tabId },
          files: ['lib/html2md.js', 'content.js']
        });
        response = await chrome.tabs.sendMessage(tabId, { action: 'getMarkdown' });
      } else {
        throw msgErr;
      }
    }

    if (!response || !response.markdown) {
      return { success: false, error: '无法获取页面内容' };
    }

    const filename = sanitizeFilename(response.title || 'untitled') + '.md';
    const dataUrl = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(response.markdown);

    const downloadId = await chrome.downloads.download({
      url: dataUrl,
      filename: filename,
      saveAs: false
    });

    return { success: true, filename: filename, downloadId: downloadId };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

function sanitizeFilename(name) {
  return name
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, '')
    .replace(/\s+/g, '_')
    .substring(0, 200)
    .trim() || 'untitled';
}
