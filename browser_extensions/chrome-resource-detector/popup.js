(function () {
  'use strict';

  var allResources = [];
  var selectedUrls = {};
  var filteredIndex = [];
  var isZipping = false;

  var el = {
    status: document.getElementById('status'),
    statsBar: document.getElementById('statsBar'),
    resourceList: document.getElementById('resourceList'),
    emptyState: document.getElementById('emptyState'),
    emptyMessage: document.getElementById('emptyMessage'),
    searchInput: document.getElementById('searchInput'),
    typeFilter: document.getElementById('typeFilter'),
    selectAllCb: document.getElementById('selectAll'),
    selectedCount: document.getElementById('selectedCount'),
    downloadSelectedBtn: document.getElementById('downloadSelected'),
    downloadZipBtn: document.getElementById('downloadZipBtn'),
    downloadAllBtn: document.getElementById('downloadAllBtn'),
    rescanBtn: document.getElementById('rescanBtn'),
    clearSearchBtn: document.getElementById('clearSearch'),
    toast: document.getElementById('toast'),
    progressBar: document.getElementById('progressBar'),
    progressBarInner: document.getElementById('progressBarInner'),
    progressLabel: document.getElementById('progressLabel')
  };

  var TYPE_ICONS = {
    image: '\uD83D\uDDBC', script: '\uD83D\uDCDC', stylesheet: '\uD83C\uDFA8',
    video: '\uD83C\uDFAC', audio: '\uD83D\uDD0A', font: '\uD83D\uDD24',
    html: '\uD83C\uDF10', document: '\uD83D\uDCC4', other: '\uD83D\uDCE6'
  };

  var toastTimer = null;

  function showToast(msg, isErr) {
    if (toastTimer) clearTimeout(toastTimer);
    el.toast.textContent = msg;
    el.toast.className = 'toast' + (isErr ? ' error' : '');
    requestAnimationFrame(function () { el.toast.classList.add('show'); });
    toastTimer = setTimeout(function () { el.toast.classList.remove('show'); }, 2500);
  }

  function setStatus(text, type) {
    el.status.textContent = text;
    el.status.className = 'status ' + (type || '');
  }

  function escapeHtml(str) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
  }

  function formatSize(bytes) {
    if (!bytes || bytes === 0) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  }

  function getTypeCounts() {
    var c = {};
    for (var i = 0; i < allResources.length; i++) {
      var t = allResources[i].type;
      c[t] = (c[t] || 0) + 1;
    }
    return c;
  }

  function getFiltered() {
    var s = el.searchInput.value.toLowerCase().trim();
    var tp = el.typeFilter.value;
    var r = [];
    for (var i = 0; i < allResources.length; i++) {
      var o = allResources[i];
      if (tp !== 'all' && o.type !== tp) continue;
      if (s && o.url.toLowerCase().indexOf(s) === -1 && o.filename.toLowerCase().indexOf(s) === -1) continue;
      r.push(i);
    }
    return r;
  }

  function renderStats() {
    var counts = getTypeCounts();
    var order = ['image', 'script', 'stylesheet', 'html', 'video', 'audio', 'font', 'document', 'other'];
    var chips = [{ type: 'all', count: allResources.length, icon: '\uD83D\uDCCA' }];
    for (var t = 0; t < order.length; t++) {
      if (counts[order[t]]) chips.push({ type: order[t], count: counts[order[t]], icon: TYPE_ICONS[order[t]] || '\uD83D\uDCE6' });
    }
    el.statsBar.innerHTML = '';
    for (var i = 0; i < chips.length; i++) {
      var chip = chips[i];
      var div = document.createElement('div');
      div.className = 'stat-chip' + (el.typeFilter.value === chip.type ? ' active' : '');
      div.innerHTML = '<span>' + chip.icon + '</span> <span>' + chip.type + '</span> <span class="count">' + chip.count + '</span>';
      (function (t) {
        div.addEventListener('click', function () {
          el.typeFilter.value = t;
          selectedUrls = {};
          render();
        });
      })(chip.type);
      el.statsBar.appendChild(div);
    }
  }

  function renderResourceList() {
    filteredIndex = getFiltered();
    if (filteredIndex.length === 0) {
      el.resourceList.innerHTML = '';
      el.emptyMessage.textContent = allResources.length ? 'No resources match the current filter' : 'No resources detected on this page';
      el.emptyState.classList.remove('hidden');
      updateActions();
      return;
    }
    el.emptyState.classList.add('hidden');
    el.resourceList.innerHTML = '';

    for (var fi = 0; fi < filteredIndex.length; fi++) {
      var idx = filteredIndex[fi];
      var r = allResources[idx];
      var sel = !!selectedUrls[r.url];
      var sizeStr = formatSize(r.size);
      var shortUrl = r.url.length > 80 ? r.url.substring(0, 80) + '...' : r.url;
      var icon = TYPE_ICONS[r.type] || '\uD83D\uDCE6';

      var item = document.createElement('div');
      item.className = 'resource-item' + (sel ? ' selected' : '');
      item.innerHTML =
        '<input type="checkbox" class="checkbox"' + (sel ? ' checked' : '') + '>' +
        '<div class="type-icon ' + r.type + '">' + icon + '</div>' +
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
        item.querySelector('.checkbox').addEventListener('change', function (e) {
          e.stopPropagation();
          toggleUrl(res.url);
        });
        item.querySelector('.download-single').addEventListener('click', function (e) {
          e.stopPropagation();
          chrome.downloads.download({
            url: res.url, filename: res.filename, conflictAction: 'uniquify', saveAs: false
          }, function () {
            if (chrome.runtime.lastError) showToast('Failed: ' + chrome.runtime.lastError.message, true);
          });
        });
        item.querySelector('.copy-url').addEventListener('click', function (e) {
          e.stopPropagation();
          navigator.clipboard.writeText(res.url).then(function () {
            showToast('URL copied');
          }, function () {
            var ta = document.createElement('textarea');
            ta.value = res.url;
            ta.style.cssText = 'position:fixed;left:-999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            showToast('URL copied');
          });
        });
      })(r);

      el.resourceList.appendChild(item);
    }
    updateActions();
  }

  function toggleUrl(url) {
    selectedUrls[url] = !selectedUrls[url];
    renderResourceList();
  }

  function updateActions() {
    var count = Object.keys(selectedUrls).length;
    el.selectedCount.textContent = count > 0 ? count + ' selected' : '0 selected';
    el.downloadSelectedBtn.disabled = count === 0;
    el.downloadZipBtn.disabled = count === 0 || isZipping;

    var filteredCount = filteredIndex.length;
    el.downloadAllBtn.disabled = filteredCount === 0 || isZipping;

    var allSel = filteredCount > 0;
    for (var i = 0; i < filteredIndex.length; i++) {
      if (!selectedUrls[allResources[filteredIndex[i]].url]) { allSel = false; break; }
    }
    el.selectAllCb.checked = allSel && filteredCount > 0;
    el.selectAllCb.indeterminate = count > 0 && !allSel;
  }

  function render() {
    renderStats();
    renderResourceList();
  }

  function setZipping(zipping) {
    isZipping = zipping;
    el.downloadZipBtn.disabled = true;
    el.downloadAllBtn.disabled = true;
    el.downloadSelectedBtn.disabled = true;
    if (zipping) {
      el.progressBar.classList.remove('hidden');
      el.progressBarInner.style.width = '0%';
      el.progressLabel.textContent = 'Preparing ZIP...';
    } else {
      el.progressBar.classList.add('hidden');
      updateActions();
    }
  }

  function startZip(items, zipName) {
    setZipping(true);
    chrome.runtime.sendMessage({
      action: 'createZip',
      items: items,
      zipName: zipName
    }, function (resp) {
      if (!resp || !resp.accepted) {
        setZipping(false);
        showToast('Failed to start ZIP creation', true);
      }
    });
  }

  function downloadSelectedAsZip() {
    var keys = Object.keys(selectedUrls);
    if (keys.length === 0) return;
    var items = [];
    for (var i = 0; i < allResources.length; i++) {
      if (selectedUrls[allResources[i].url]) {
        var r = allResources[i];
        items.push({ url: r.url, filename: r.filename, pathname: r.pathname, htmlContent: r.htmlContent || null });
      }
    }
    startZip(items, 'resources.zip');
  }

  function downloadAllVisibleAsZip() {
    var items = [];
    for (var i = 0; i < filteredIndex.length; i++) {
      var r = allResources[filteredIndex[i]];
      items.push({ url: r.url, filename: r.filename, pathname: r.pathname, htmlContent: r.htmlContent || null });
    }
    if (items.length === 0) return;
    startZip(items, 'resources.zip');
  }

  function downloadSelectedIndividual() {
    var keys = Object.keys(selectedUrls);
    if (keys.length === 0) return;
    var resourceMap = {};
    for (var i = 0; i < allResources.length; i++) resourceMap[allResources[i].url] = allResources[i];

    var urls = keys.slice();
    var idx = 0;
    function next() {
      if (idx >= urls.length) { showToast(urls.length + ' resource(s) queued'); return; }
      var batch = Math.min(idx + 5, urls.length);
      for (var i = idx; i < batch; i++) {
        var r = resourceMap[urls[i]];
        chrome.downloads.download({
          url: urls[i], filename: r ? r.filename : 'resource',
          conflictAction: 'uniquify', saveAs: false
        }, function () { if (chrome.runtime.lastError) console.warn(chrome.runtime.lastError.message); });
      }
      idx = batch;
      if (idx < urls.length) setTimeout(next, 600);
    }
    next();
    showToast('Downloading ' + urls.length + ' file(s)...');
  }

  function loadResources() {
    setStatus('Scanning...', 'loading');
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      var tab = tabs && tabs[0];
      if (!tab || !tab.id) { setStatus('No active tab', 'error'); return; }

      var restricted = tab.url && (
        tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://') ||
        tab.url.startsWith('about:') || tab.url.startsWith('edge://') || tab.url.startsWith('brave://')
      );
      if (restricted) {
        allResources = []; selectedUrls = {};
        setStatus('Not available', 'error');
        el.emptyMessage.textContent = 'Not available on this type of page';
        render();
        return;
      }

      chrome.tabs.sendMessage(tab.id, { action: 'getResources' }, function (resp) {
        if (chrome.runtime.lastError || !resp) {
          allResources = []; selectedUrls = {};
          setStatus('Cannot access page', 'error');
          el.emptyMessage.textContent = 'Try refreshing the page and reopening the popup.';
          render();
          return;
        }
        allResources = resp.resources || [];
        selectedUrls = {};
        setStatus(allResources.length + ' resources found', 'success');
        render();
      });
    });
  }

  chrome.runtime.onMessage.addListener(function (msg) {
    if (msg.action === 'zipProgress') {
      var pct = msg.total > 0 ? Math.round((msg.current / msg.total) * 100) : 0;
      el.progressBarInner.style.width = pct + '%';
      if (msg.status === 'packing') {
        el.progressLabel.textContent = 'Packing ZIP...';
      } else if (msg.status === 'error') {
        el.progressLabel.textContent = 'Skipped: ' + msg.filename;
      } else {
        el.progressLabel.textContent = msg.current + '/' + msg.total + ' ' + msg.filename;
      }
    } else if (msg.action === 'zipComplete') {
      setZipping(false);
      showToast('ZIP saved: ' + msg.filename + ' (' + (msg.fileCount || '') + ' files)');
    } else if (msg.action === 'zipError') {
      setZipping(false);
      showToast(msg.message || 'ZIP creation failed', true);
    }
  });

  el.searchInput.addEventListener('input', function () { selectedUrls = {}; renderResourceList(); });
  el.clearSearchBtn.addEventListener('click', function () { el.searchInput.value = ''; selectedUrls = {}; render(); });
  el.typeFilter.addEventListener('change', function () { selectedUrls = {}; render(); });

  el.selectAllCb.addEventListener('change', function () {
    if (el.selectAllCb.checked) {
      for (var i = 0; i < filteredIndex.length; i++) selectedUrls[allResources[filteredIndex[i]].url] = true;
    } else {
      for (var i = 0; i < filteredIndex.length; i++) delete selectedUrls[allResources[filteredIndex[i]].url];
    }
    renderResourceList();
  });

  el.downloadSelectedBtn.addEventListener('click', downloadSelectedIndividual);
  el.downloadZipBtn.addEventListener('click', downloadSelectedAsZip);
  el.downloadAllBtn.addEventListener('click', downloadAllVisibleAsZip);
  el.rescanBtn.addEventListener('click', loadResources);

  el.searchInput.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { el.searchInput.value = ''; selectedUrls = {}; render(); }
  });

  loadResources();
})();
