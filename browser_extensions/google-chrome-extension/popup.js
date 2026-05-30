const saveBtn = document.getElementById('saveBtn');
const statusEl = document.getElementById('status');
const titlePreview = document.getElementById('titlePreview');

let currentTabId = null;

async function init() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      showStatus('无法获取当前标签页', 'error');
      return;
    }

    currentTabId = tab.id;

    if (tab.url && tab.url.startsWith('chrome://')) {
      saveBtn.disabled = true;
      titlePreview.textContent = '无法在 Chrome 内部页面使用';
      showStatus('请在普通网页上使用此功能', 'error');
      return;
    }

    titlePreview.textContent = tab.title || tab.url || '未知页面';
    saveBtn.addEventListener('click', handleSave);
  } catch (err) {
    showStatus('初始化失败: ' + err.message, 'error');
  }
}

async function handleSave() {
  if (!currentTabId) {
    showStatus('请先打开一个网页', 'error');
    return;
  }

  saveBtn.disabled = true;
  saveBtn.textContent = '正在保存...';
  showStatus('', '');

  try {
    const response = await chrome.runtime.sendMessage({
      action: 'saveMarkdown',
      tabId: currentTabId
    });

    if (response.success) {
      showStatus('已保存: ' + response.filename, 'success');
    } else {
      showStatus('保存失败: ' + (response.error || '未知错误'), 'error');
    }
  } catch (err) {
    showStatus('通信错误: ' + err.message, 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = '保存为 Markdown';
  }
}

function showStatus(msg, type) {
  statusEl.textContent = msg;
  statusEl.className = 'status ' + type;
}

document.addEventListener('DOMContentLoaded', init);
