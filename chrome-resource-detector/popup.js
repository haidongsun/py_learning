(function () {
  'use strict';

  var allResources = [];
  var selectedUrls = {};
  var filteredIndex = [];

  var statusEl = document.getElementById('status');
  var statsBar = document.getElementById('statsBar');
  var resourceList = document.getElementById('resourceList');
  var emptyState = document.getElementById('emptyState');
  var emptyMessage = document.getElementById('emptyMessage');
  var searchInput = document.getElementById('searchInput');
  var typeFilter = document.getElementById('typeFilter');
  var selectAllCb = document.getElementById('selectAll');
  var selectedCountEl = document.getElementById('selectedCount');
  var downloadSelectedBtn = document.getElementById('downloadSelected');
  var downloadAllBtn = document.getElementById('downloadAll');
  var rescanBtn = document.getElementById('rescanBtn');
  var clearSearchBtn = document.getElementById('clearSearch');
  var toastEl = document.getElementById('toast');

  var TYPE_ICONS = {
    image: '\uD83D\uDDBC',
    script: '\uD83D\uDCDC',
    stylesheet: '\uD83C\uDFA8',
    video: '\uD83C\uDFAC',
    audio: '\uD83D\uDD0A',
    font: '\uD83D\uDD24',
    document: '\uD83D\uDCC4',
    other: '\uD83D\uDCE6'
  };

  var toastTimer = null;

  function showToast(message, isError) {
    if (toastTimer) clearTimeout(toastTimer);
    toastEl.textContent = message;
    toastEl.className = 'toast' + (isError ? ' error' : '');
    requestAnimationFrame(function () {
      toastEl.classList.add('show');
    });
    toastTimer = setTimeout(function () {
      toastEl.classList.remove('show');
    }, 2000);
  }

  function setStatus(text, type) {
    statusEl.textContent = text;
    statusEl.className = 'status ' + (type || '');
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function getTypeCounts() {
    var counts = {};
    for (var i = 0; i < allResources.length; i++) {
      var type = allResources[i].type;
      counts[type] = (counts[type] || 0) + 1;
    }
    return counts;
  }

  function formatSize(bytes) {
    if (!bytes || bytes === 0) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function getFiltered() {
    var searchTerm = searchInput.value.toLowerCase().trim();
    var type = typeFilter.value;

    var result = [];
    for (var i = 0; i < allResources.length; i++) {
      var r = allResources[i];
      var matchesType = type === 'all' || r.type === type;
      var matchesSearch = !searchTerm ||
        r.url.toLowerCase().indexOf(searchTerm) !== -1 ||
        r.filename.toLowerCase().indexOf(searchTerm) !== -1;
      if (matchesType && matchesSearch) {
        result.push(i);
      }
    }
    return result;
  }

  function renderStats() {
    var counts = getTypeCounts();
    var chips = [{ type: 'all', count: allResources.length, icon: '\uD83D\uDCCA' }];
    var typeOrder = ['image', 'script', 'stylesheet', 'video', 'audio', 'font', 'document', 'other'];

    for (var t = 0; t < typeOrder.length; t++) {
      if (counts[typeOrder[t]]) {
        chips.push({ type: typeOrder[t], count: counts[typeOrder[t]], icon: TYPE_ICONS[typeOrder[t]] || '\uD83D\uDCE6' });
      }
    }

    statsBar.innerHTML = '';
    for (var i = 0; i < chips.length; i++) {
      var chip = chips[i];
      var el = document.createElement('div');
      el.className = 'stat-chip' + (typeFilter.value === chip.type ? ' active' : '');
      el.dataset.type = chip.type;
      el.innerHTML = '<span>' + chip.icon + '</span> <span>' + chip.type + '</span> <span class="count">' + chip.count + '</span>';
      el.addEventListener('click', function () {
        typeFilter.value = this.dataset.type;
        selectedUrls = {};
        render();
      });
      statsBar.appendChild(el);
    }
  }

  function renderResourceList() {
    filteredIndex = getFiltered();

    if (filteredIndex.length === 0) {
      resourceList.innerHTML = '';
      if (allResources.length === 0) {
        emptyMessage.textContent = 'No resources detected on this page';
      } else {
        emptyMessage.textContent = 'No resources match the current filter';
      }
      emptyState.classList.remove('hidden');
      updateSelectionUI();
      return;
    }

    emptyState.classList.add('hidden');

    resourceList.innerHTML = '';
    for (var fi = 0; fi < filteredIndex.length; fi++) {
      var idx = filteredIndex[fi];
      var r = allResources[idx];
      var isSelected = !!selectedUrls[r.url];
      var sizeStr = formatSize(r.size);
      var shortUrl = r.url.length > 80 ? r.url.substring(0, 80) + '...' : r.url;

      var item = document.createElement('div');
      item.className = 'resource-item' + (isSelected ? ' selected' : '');
      item.dataset.fi = fi;

      var typeIcon = TYPE_ICONS[r.type] || '\uD83D\uDCE6';

      item.innerHTML =
        '<input type="checkbox" class="checkbox"' + (isSelected ? ' checked' : '') + '>' +
        '<div class="type-icon ' + r.type + '">' + typeIcon + '</div>' +
        '<div class="info">' +
          '<div class="filename" title="' + escapeHtml(r.filename) + '">' + escapeHtml(r.filename) + '</div>' +
          '<div class="url-text" title="' + escapeHtml(r.url) + '">' + escapeHtml(shortUrl) + '</div>' +
        '</div>' +
        (sizeStr ? '<div class="size-text">' + escapeHtml(sizeStr) + '</div>' : '') +
        '<div class="actions">' +
          '<button class="btn-sm download-single">Save</button>' +
          '<button class="btn-sm copy-url">Copy</button>' +
        '</div>';

      (function (res) {
        item.addEventListener('click', function (e) {
          if (e.target.tagName === 'INPUT' || e.target.closest('button')) return;
          toggleUrl(res.url);
        });

        var cb = item.querySelector('.checkbox');
        cb.addEventListener('change', function (e) {
          e.stopPropagation();
          toggleUrl(res.url);
        });

        var dlBtn = item.querySelector('.download-single');
        dlBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          downloadOne(res.url, res.filename);
        });

        var cpBtn = item.querySelector('.copy-url');
        cpBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          copyUrl(res.url);
        });
      })(r);

      resourceList.appendChild(item);
    }

    updateSelectionUI();
  }

  function toggleUrl(url) {
    if (selectedUrls[url]) {
      delete selectedUrls[url];
    } else {
      selectedUrls[url] = true;
    }
    renderResourceList();
  }

  function updateSelectionUI() {
    var count = Object.keys(selectedUrls).length;
    selectedCountEl.textContent = count > 0 ? count + ' selected' : '0 selected';
    downloadSelectedBtn.disabled = count === 0;

    var allFilteredSelected = filteredIndex.length > 0;
    for (var i = 0; i < filteredIndex.length; i++) {
      if (!selectedUrls[allResources[filteredIndex[i]].url]) {
        allFilteredSelected = false;
        break;
      }
    }
    selectAllCb.checked = allFilteredSelected && filteredIndex.length > 0;
    selectAllCb.indeterminate = count > 0 && !allFilteredSelected;
  }

  function render() {
    renderStats();
    renderResourceList();
  }

  function downloadOne(url, filename) {
    chrome.downloads.download({
      url: url,
      filename: filename || 'resource',
      conflictAction: 'uniquify',
      saveAs: false
    }, function (downloadId) {
      if (chrome.runtime.lastError) {
        showToast('Download failed: ' + chrome.runtime.lastError.message, true);
      }
    });
  }

  function copyUrl(url) {
    try {
      navigator.clipboard.writeText(url).then(function () {
        showToast('URL copied');
      }, function () {
        var ta = document.createElement('textarea');
        ta.value = url;
        ta.style.position = 'fixed';
        ta.style.left = '-999px';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('URL copied');
      });
    } catch (e) {
      showToast('Failed to copy', true);
    }
  }

  function downloadSelected() {
    var urls = Object.keys(selectedUrls);
    if (urls.length === 0) return;
    batchDownload(urls);
  }

  function downloadAllVisible() {
    var urls = [];
    for (var i = 0; i < filteredIndex.length; i++) {
      urls.push(allResources[filteredIndex[i]].url);
    }
    if (urls.length === 0) return;
    batchDownload(urls);
  }

  function batchDownload(urls) {
    var resourceMap = {};
    for (var i = 0; i < allResources.length; i++) {
      resourceMap[allResources[i].url] = allResources[i];
    }

    var batchSize = 5;
    var index = 0;
    var total = urls.length;

    function nextBatch() {
      if (index >= urls.length) {
        showToast(total + ' resource(s) queued for download');
        return;
      }

      var end = Math.min(index + batchSize, urls.length);
      for (var i = index; i < end; i++) {
        var url = urls[i];
        var res = resourceMap[url];
        chrome.downloads.download({
          url: url,
          filename: res ? res.filename : 'resource',
          conflictAction: 'uniquify',
          saveAs: false
        }, function (downloadId) {
          if (chrome.runtime.lastError) {
            console.warn('Batch download error:', chrome.runtime.lastError.message);
          }
        });
      }
      index = end;
      setTimeout(nextBatch, 600);
    }

    nextBatch();
  }

  function loadResources() {
    setStatus('Scanning...', 'loading');

    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      if (!tabs || !tabs[0] || !tabs[0].id) {
        setStatus('No active tab', 'error');
        return;
      }

      var tab = tabs[0];
      var restricted = tab.url && (
        tab.url.startsWith('chrome://') ||
        tab.url.startsWith('chrome-extension://') ||
        tab.url.startsWith('about:') ||
        tab.url.startsWith('edge://') ||
        tab.url.startsWith('brave://')
      );

      if (restricted) {
        allResources = [];
        selectedUrls = {};
        setStatus('Not available on this page', 'error');
        emptyMessage.textContent = 'Resource detection is not available on this type of page';
        render();
        return;
      }

      chrome.tabs.sendMessage(tab.id, { action: 'getResources' }, function (response) {
        if (chrome.runtime.lastError || !response) {
          setStatus('Cannot access this page', 'error');
          emptyMessage.textContent = 'Cannot detect resources on this page. Try refreshing and reopening the popup.';
          allResources = [];
          selectedUrls = {};
          render();
          return;
        }

        allResources = response.resources || [];
        selectedUrls = {};
        setStatus(allResources.length + ' resources found', 'success');
        render();
      });
    });
  }

  searchInput.addEventListener('input', function () {
    selectedUrls = {};
    renderResourceList();
  });

  clearSearchBtn.addEventListener('click', function () {
    searchInput.value = '';
    selectedUrls = {};
    render();
  });

  typeFilter.addEventListener('change', function () {
    selectedUrls = {};
    render();
  });

  selectAllCb.addEventListener('change', function () {
    if (selectAllCb.checked) {
      for (var i = 0; i < filteredIndex.length; i++) {
        selectedUrls[allResources[filteredIndex[i]].url] = true;
      }
    } else {
      for (var i = 0; i < filteredIndex.length; i++) {
        delete selectedUrls[allResources[filteredIndex[i]].url];
      }
    }
    renderResourceList();
  });

  downloadSelectedBtn.addEventListener('click', downloadSelected);
  downloadAllBtn.addEventListener('click', downloadAllVisible);
  rescanBtn.addEventListener('click', loadResources);

  searchInput.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      searchInput.value = '';
      selectedUrls = {};
      render();
    }
  });

  loadResources();
})();
