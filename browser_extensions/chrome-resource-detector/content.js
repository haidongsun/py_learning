(function () {
  'use strict';

  var resources = new Map();
  var performanceObserver = null;
  var mutationObserver = null;
  var initialized = false;
  var pageUrl = window.location.href;
  var pageOrigin = window.location.origin;

  var IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp', 'avif', 'tiff'];
  var VIDEO_EXTS = ['mp4', 'webm', 'ogg', 'ogv', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'm4v'];
  var AUDIO_EXTS = ['mp3', 'wav', 'aac', 'flac', 'oga', 'm4a', 'wma', 'opus'];
  var FONT_EXTS = ['woff', 'woff2', 'ttf', 'otf', 'eot'];
  var SCRIPT_EXTS = ['js', 'mjs', 'cjs', 'ts'];
  var HTML_EXTS = ['html', 'htm'];

  function getFileExtension(url) {
    try {
      var pathname = url.split('?')[0].split('#')[0];
      var parts = pathname.split('.');
      return parts.length > 1 ? parts.pop().toLowerCase() : '';
    } catch (e) { return ''; }
  }

  function getResourceType(url, elementType, initiatorType) {
    var ext = getFileExtension(url);
    if (url === pageUrl && (ext === 'html' || ext === 'htm' || ext === '' ||
        elementType === 'html' || initiatorType === 'navigation')) return 'html';
    if (HTML_EXTS.indexOf(ext) !== -1) return 'html';
    if (elementType === 'img' || elementType === 'image' || initiatorType === 'img') return 'image';
    if (elementType === 'script' || initiatorType === 'script') return 'script';
    if (elementType === 'stylesheet' || initiatorType === 'link') return 'stylesheet';
    if (ext === 'css') return 'stylesheet';
    if (elementType === 'video' || initiatorType === 'video') return 'video';
    if (elementType === 'audio' || initiatorType === 'audio') return 'audio';
    if (elementType === 'font' || initiatorType === 'font') return 'font';
    if (elementType === 'document' || initiatorType === 'iframe') return 'document';
    if (FONT_EXTS.indexOf(ext) !== -1) return 'font';
    if (IMAGE_EXTS.indexOf(ext) !== -1) return 'image';
    if (VIDEO_EXTS.indexOf(ext) !== -1) return 'video';
    if (AUDIO_EXTS.indexOf(ext) !== -1) return 'audio';
    if (SCRIPT_EXTS.indexOf(ext) !== -1) return 'script';
    if (ext === 'xml') return 'document';
    return 'other';
  }

  function getFilename(url) {
    try {
      var urlObj = new URL(url);
      var pathname = urlObj.pathname;
      var filename = pathname.split('/').pop();
      if (filename && filename.indexOf('.') !== -1) return filename;
      if (filename) return filename;
      return urlObj.hostname + '.html';
    } catch (e) { return 'resource'; }
  }

  function sanitizeFilename(name) {
    return name.replace(/[<>:"|?*\x00-\x1f]/g, '_').substring(0, 200);
  }

  function getPathname(url) {
    try {
      var urlObj = new URL(url);
      if (urlObj.origin === pageOrigin) {
        var path = urlObj.pathname;
        if (path === '/' || path === '') return 'index.html';
        var result = path.substring(1);
        if (result.indexOf('.') === -1) result += '.html';
        return result;
      } else {
        var hostPath = urlObj.hostname + urlObj.pathname;
        return 'external/' + hostPath.replace(/\/+$/, '');
      }
    } catch (e) {
      return getFilename(url);
    }
  }

  function addResource(url, elementType, size, initiatorType) {
    if (!url) return;
    if (url.startsWith('chrome-extension://') || url.startsWith('moz-extension://')) return;
    if (url.startsWith('about:') || url.startsWith('javascript:')) return;
    if (url.startsWith('data:') && url.length > 500) return;

    if (resources.has(url)) {
      var existing = resources.get(url);
      if (size && !existing.size) existing.size = size;
      return;
    }

    var resourceType = getResourceType(url, elementType, initiatorType);
    var filename = sanitizeFilename(getFilename(url));
    var pathname = getPathname(url);

    resources.set(url, {
      url: url,
      type: resourceType,
      filename: filename,
      pathname: pathname,
      size: size || 0,
      timestamp: Date.now()
    });
  }

  function setupPerformanceObserver() {
    try {
      var entries = performance.getEntriesByType('resource');
      for (var i = 0; i < entries.length; i++) {
        var entry = entries[i];
        var size = entry.transferSize || entry.encodedBodySize || 0;
        addResource(entry.name, null, size, entry.initiatorType);
      }

      performanceObserver = new PerformanceObserver(function (list) {
        var newEntries = list.getEntries();
        for (var i = 0; i < newEntries.length; i++) {
          var entry = newEntries[i];
          var size = entry.transferSize || entry.encodedBodySize || 0;
          addResource(entry.name, null, size, entry.initiatorType);
        }
      });

      try { performanceObserver.observe({ type: 'resource', buffered: true }); }
      catch (e) { performanceObserver.observe({ type: 'resource' }); }
    } catch (e) {}
  }

  function extractUrlsFromCss(cssText) {
    var urls = [];
    var regex = /url\(\s*["']?([^"')]+)["']?\s*\)/g;
    var match;
    while ((match = regex.exec(cssText)) !== null) {
      if (match[1] && !match[1].startsWith('data:')) urls.push(match[1]);
    }
    return urls;
  }

  function scanDomElements() {
    var els, i, j, k;

    els = document.querySelectorAll('img[src]');
    for (i = 0; i < els.length; i++) {
      addResource(els[i].src, 'img', 0, 'img');
      if (els[i].srcset) {
        var parts = els[i].srcset.split(',');
        for (j = 0; j < parts.length; j++) {
          var u = parts[j].trim().split(' ')[0];
          if (u) addResource(u, 'img', 0, 'img');
        }
      }
    }

    els = document.querySelectorAll('script[src]');
    for (i = 0; i < els.length; i++) addResource(els[i].src, 'script', 0, 'script');

    els = document.querySelectorAll('link[href]');
    for (i = 0; i < els.length; i++) {
      var rel = els[i].rel || '';
      if (rel === 'stylesheet') addResource(els[i].href, 'stylesheet', 0, 'link');
      else if (rel.indexOf('icon') !== -1) addResource(els[i].href, 'img', 0, 'img');
      else addResource(els[i].href, 'other', 0, 'link');
    }

    els = document.querySelectorAll('video[src]');
    for (i = 0; i < els.length; i++) {
      addResource(els[i].src, 'video', 0, 'video');
      if (els[i].poster) addResource(els[i].poster, 'img', 0, 'img');
    }

    els = document.querySelectorAll('video source[src]');
    for (i = 0; i < els.length; i++) addResource(els[i].src, 'video', 0, 'video');
    els = document.querySelectorAll('video source[srcset]');
    for (i = 0; i < els.length; i++) {
      parts = els[i].srcset.split(',');
      for (j = 0; j < parts.length; j++) {
        u = parts[j].trim().split(' ')[0];
        if (u) addResource(u, 'video', 0, 'video');
      }
    }

    els = document.querySelectorAll('audio[src]');
    for (i = 0; i < els.length; i++) addResource(els[i].src, 'audio', 0, 'audio');
    els = document.querySelectorAll('audio source[src]');
    for (i = 0; i < els.length; i++) addResource(els[i].src, 'audio', 0, 'audio');

    els = document.querySelectorAll('iframe[src]');
    for (i = 0; i < els.length; i++) addResource(els[i].src, 'document', 0, 'iframe');
    els = document.querySelectorAll('object[data]');
    for (i = 0; i < els.length; i++) addResource(els[i].data, 'other', 0, 'object');
    els = document.querySelectorAll('embed[src]');
    for (i = 0; i < els.length; i++) addResource(els[i].src, 'other', 0, 'embed');
    els = document.querySelectorAll('input[type="image"][src]');
    for (i = 0; i < els.length; i++) addResource(els[i].src, 'img', 0, 'img');

    els = document.querySelectorAll('[style]');
    for (i = 0; i < els.length; i++) {
      var styleVal = els[i].getAttribute('style');
      var cssUrls = extractUrlsFromCss(styleVal);
      for (k = 0; k < cssUrls.length; k++) addResource(cssUrls[k], 'img', 0, 'img');
    }

    els = document.querySelectorAll('source[srcset]');
    for (i = 0; i < els.length; i++) {
      parts = els[i].srcset.split(',');
      var isVideo = !!els[i].closest('video');
      for (j = 0; j < parts.length; j++) {
        u = parts[j].trim().split(' ')[0];
        if (u) addResource(u, isVideo ? 'video' : 'img', 0, 'source');
      }
    }
  }

  function scanCssResources() {
    try {
      var sheets = document.styleSheets;
      for (var i = 0; i < sheets.length; i++) {
        try {
          var rules = sheets[i].cssRules || sheets[i].rules;
          if (!rules) continue;
          for (var j = 0; j < rules.length; j++) {
            var text = rules[j].cssText || '';
            var urls = extractUrlsFromCss(text);
            for (var k = 0; k < urls.length; k++) {
              try {
                var base = sheets[i].href || window.location.href;
                addResource(new URL(urls[k], base).href, 'other', 0, 'css');
              } catch (e) {}
            }
          }
        } catch (e) {}
      }
    } catch (e) {}
  }

  function checkElement(el) {
    var tag = el.tagName, styleAttr, urls, j;
    if (tag === 'IMG' && el.src) addResource(el.src, 'img', 0, 'img');
    else if (tag === 'SCRIPT' && el.src) addResource(el.src, 'script', 0, 'script');
    else if (tag === 'LINK' && el.href) {
      if (el.rel === 'stylesheet') addResource(el.href, 'stylesheet', 0, 'link');
      else if (el.rel && el.rel.indexOf('icon') !== -1) addResource(el.href, 'img', 0, 'img');
      else addResource(el.href, 'other', 0, 'link');
    } else if (tag === 'VIDEO') {
      if (el.src) addResource(el.src, 'video', 0, 'video');
      if (el.poster) addResource(el.poster, 'img', 0, 'img');
    } else if (tag === 'AUDIO' && el.src) addResource(el.src, 'audio', 0, 'audio');
    else if (tag === 'SOURCE' && (el.src || el.srcset)) addResource(el.src || el.srcset, 'other', 0, 'source');
    else if (tag === 'IFRAME' && el.src) addResource(el.src, 'document', 0, 'iframe');
    else if (tag === 'OBJECT' && el.data) addResource(el.data, 'other', 0, 'object');
    else if (tag === 'EMBED' && el.src) addResource(el.src, 'other', 0, 'embed');
    else if (tag === 'INPUT' && el.type === 'image' && el.src) addResource(el.src, 'img', 0, 'img');

    if (el.hasAttribute && el.hasAttribute('style')) {
      styleAttr = el.getAttribute('style');
      urls = extractUrlsFromCss(styleAttr);
      for (j = 0; j < urls.length; j++) addResource(urls[j], 'img', 0, 'img');
    }
  }

  function setupMutationObserver() {
    mutationObserver = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var nodes = mutations[i].addedNodes;
        for (var j = 0; j < nodes.length; j++) {
          if (nodes[j].nodeType !== 1) continue;
          checkElement(nodes[j]);
          if (nodes[j].querySelectorAll) {
            var children = nodes[j].querySelectorAll('img[src], script[src], link[href], video[src], video[poster], audio[src], source[src], source[srcset], iframe[src], object[data], embed[src], input[type="image"][src], [style]');
            for (var k = 0; k < children.length; k++) checkElement(children[k]);
          }
        }
      }
    });
    mutationObserver.observe(document.documentElement, { childList: true, subtree: true });
  }

  function getTypeCounts(arr) {
    var counts = {};
    for (var i = 0; i < arr.length; i++) {
      var t = arr[i].type;
      counts[t] = (counts[t] || 0) + 1;
    }
    return counts;
  }

  function initialize() {
    if (initialized) return;
    initialized = true;
    setupPerformanceObserver();
    addResource(pageUrl, 'html', 0, 'navigation');
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        scanDomElements();
        scanCssResources();
        setupMutationObserver();
      });
    } else {
      scanDomElements();
      scanCssResources();
      setupMutationObserver();
    }
  }

  chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    if (message.action === 'getResources') {
      scanDomElements();
      scanCssResources();
      var arr = [];
      var it = resources.values();
      var next = it.next();
      while (!next.done) { arr.push(next.value); next = it.next(); }
      arr.sort(function (a, b) {
        if (a.type !== b.type) return a.type.localeCompare(b.type);
        return a.filename.localeCompare(b.filename);
      });
      for (var i = 0; i < arr.length; i++) {
        if (arr[i].url === pageUrl && arr[i].type === 'html') {
          try {
            var html = document.documentElement.outerHTML;
            arr[i].htmlContent = btoa(unescape(encodeURIComponent(html)));
          } catch (e) {}
        }
      }
      sendResponse({ resources: arr, total: arr.length, types: getTypeCounts(arr) });
      return true;
    }
    if (message.action === 'ping') {
      sendResponse({ pong: true, ready: initialized });
      return false;
    }
    return false;
  });

  initialize();
})();
