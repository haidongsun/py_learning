try {
  importScripts('lib/zip.js');
} catch (e) {
  console.error('Resource Detector: Failed to load zip library', e);
}

var MAX_TOTAL_SIZE = 200 * 1024 * 1024;

function uint8ToBase64(bytes) {
  var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  var result = '';
  var len = bytes.length;
  for (var i = 0; i < len; i += 3) {
    var b1 = bytes[i];
    var b2 = i + 1 < len ? bytes[i + 1] : 0;
    var b3 = i + 2 < len ? bytes[i + 2] : 0;
    result += chars[b1 >> 2];
    result += chars[((b1 & 3) << 4) | (b2 >> 4)];
    result += i + 1 < len ? chars[((b2 & 15) << 2) | (b3 >> 6)] : '=';
    result += i + 2 < len ? chars[b3 & 63] : '=';
  }
  return result;
}

function sanitizeName(name) {
  return name.replace(/[<>:"\\|?*\x00-\x1f]/g, '_').substring(0, 200);
}

function sanitizePath(name) {
  return name.split('/').map(function (seg) {
    return seg.replace(/[<>:"\\|?*\x00-\x1f]/g, '_').substring(0, 200);
  }).join('/');
}

function notifyProgress(current, total, filename, status, errorMsg) {
  chrome.runtime.sendMessage({
    action: 'zipProgress',
    current: current,
    total: total,
    filename: filename || '',
    status: status || 'fetching',
    error: errorMsg || ''
  }).catch(function () {});
}

function notifyError(message) {
  chrome.runtime.sendMessage({
    action: 'zipError',
    message: message
  }).catch(function () {});
}

function notifyComplete(zipName, fileCount) {
  chrome.runtime.sendMessage({
    action: 'zipComplete',
    filename: zipName,
    fileCount: fileCount
  }).catch(function () {});
}

function generateZipName() {
  var now = new Date();
  var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
  return 'resources_' +
    now.getFullYear() +
    pad(now.getMonth() + 1) +
    pad(now.getDate()) + '_' +
    pad(now.getHours()) +
    pad(now.getMinutes()) +
    pad(now.getSeconds()) + '.zip';
}

async function createAndDownloadZip(items, zipName) {
  var zip = new self.ZipWriter();
  var totalSize = 0;
  var successCount = 0;

  for (var i = 0; i < items.length; i++) {
    var item = items[i];

    try {
      notifyProgress(i + 1, items.length, item.filename, 'fetching');

      var buffer;

      if (item.htmlContent) {
        var binary = atob(item.htmlContent);
        var bytes = new Uint8Array(binary.length);
        for (var b = 0; b < binary.length; b++) bytes[b] = binary.charCodeAt(b);
        buffer = bytes.buffer;
      } else {
        var response = await fetch(item.url, {
          method: 'GET',
          mode: 'cors',
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('HTTP ' + response.status);
        }

        buffer = await response.arrayBuffer();
      }

      totalSize += buffer.byteLength;

      if (totalSize > MAX_TOTAL_SIZE) {
        notifyError('Total file size exceeds 200MB limit. Try selecting fewer resources.');
        return;
      }

      var safeName = sanitizePath(item.pathname || sanitizeName(item.filename));
      if (!safeName || safeName === '_') {
        var ext = item.url.split('?')[0].split('.').pop().toLowerCase();
        safeName = 'resource_' + (i + 1) + (ext ? '.' + ext : '');
      }

      zip.addFile(safeName, new Uint8Array(buffer));
      successCount++;

      notifyProgress(i + 1, items.length, item.filename, 'added');

    } catch (e) {
      notifyProgress(i + 1, items.length, item.filename, 'error', e.message || 'Fetch failed');
    }
  }

  if (successCount === 0) {
    notifyError('Could not fetch any resources. Check network and try again.');
    return;
  }

  notifyProgress(items.length, items.length, '', 'packing');

  var zipData = zip.generate();

  try {
    var base64 = uint8ToBase64(zipData);
    var dataUrl = 'data:application/zip;base64,' + base64;

    chrome.downloads.download({
      url: dataUrl,
      filename: zipName || generateZipName(),
      conflictAction: 'uniquify',
      saveAs: false
    }, function (downloadId) {
      if (chrome.runtime.lastError) {
        notifyError('Download failed: ' + chrome.runtime.lastError.message);
      } else {
        notifyComplete(zipName || 'resources.zip', successCount);
      }
    });
  } catch (e) {
    notifyError('Failed to create ZIP: ' + (e.message || 'unknown error'));
  }
}

chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
  if (message.action === 'createZip') {
    sendResponse({ accepted: true });
    createAndDownloadZip(message.items, message.zipName);
    return false;
  }
  return false;
});
