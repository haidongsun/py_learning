chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getMarkdown') {
    try {
      const markdown = html2md(document.body);
      const title = document.title || window.location.hostname || 'untitled';
      sendResponse({ markdown: markdown, title: title });
    } catch (err) {
      sendResponse({ markdown: null, error: err.message });
    }
    return true;
  }
});
