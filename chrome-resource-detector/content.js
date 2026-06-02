(function () {
  'use strict';

  var resources = new Map();
  var performanceObserver = null;
  var mutationObserver = null;
  var initialized = false;

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

  var IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp', 'avif', 'tiff', 'tif'];
  var VIDEO_EXTS = ['mp4', 'webm', 'ogg', 'ogv', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'm4v'];
  var AUDIO_EXTS = ['mp3', 'wav', 'aac', 'flac', 'ogg', 'oga', 'm4a', 'wma', 'opus'];
  var FONT_EXTS = ['woff', 'woff2', 'ttf', 'otf', 'eot'];
  var SCRIPT_EXTS = ['js', 'mjs', 'cjs', 'ts'];

  function getFileExtension(url) {
    try {
      var pathname = url.split('?')[0].split('#')[0];
      var parts = pathname.split('.');
      return parts.length > 1 ? parts.pop().toLowerCase() : '';
    } catch (e) {
      return '';
    }
  }

  function getResourceType(url, elementType, initiatorType) {
    var ext = getFileExtension(url);

    if (elementType === 'img' || elementType === 'image' || initiatorType === 'img' || initiatorType === 'image') return 'image';
    if (elementType === 'script' || initiatorType === 'script') return 'script';
    if (elementType === 'stylesheet' || initiatorType === 'link' || ext === 'css') return 'stylesheet';
    if (elementType === 'video' || initiatorType === 'video') return 'video';
    if (elementType === 'audio' || initiatorType === 'audio') return 'audio';
    if (elementType === 'font' || initiatorType === 'font') return 'font';
    if (elementType === 'document' || initiatorType === 'iframe') return 'document';
    if (FONT_EXTS.indexOf(ext) !== -1) return 'font';
    if (IMAGE_EXTS.indexOf(ext) !== -1) return 'image';
    if (VIDEO_EXTS.indexOf(ext) !== -1) return 'video';
    if (AUDIO_EXTS.indexOf(ext) !== -1) return 'audio';
    if (SCRIPT_EXTS.indexOf(ext) !== -1) return 'script';
    if (ext === 'html' || ext === 'htm' || ext === 'xml') return 'document';

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
    } catch (e) {
      return 'resource';
    }
  }

  function sanitizeFilename(name) {
    return name.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').substring(0, 200);
  }

  function addResource(url, elementType, size, initiatorType) {
    if (!url) return;
    if (url.startsWith('chrome-extension://') || url.startsWith('moz-extension://')) return;
    if (url.startsWith('about:') || url.startsWith('javascript:')) return;

    if (resources.has(url)) {
      var existing = resources.get(url);
      if (size && !existing.size) existing.size = size;
      return;
    }

    var resourceType = getResourceType(url, elementType, initiatorType);
    var filename = sanitizeFilename(getFilename(url));

    resources.set(url, {
      url: url,
      type: resourceType,
      filename: filename,
      size: size || 0,
      timestamp: Date.now()
    });
  }

  function setupPerformanceObserver() {
    try {
      var entries = performance.getEntriesByType('resource');
      for (var i = 0; i < entries.length; i++) {
        var entry = entries[i];
        var size = entry.transferSize || entry.encodedBodySize || entry.decodedBodySize || 0;
        addResource(entry.name, null, size, entry.initiatorType);
      }

      performanceObserver = new PerformanceObserver(function (list) {
        var newEntries = list.getEntries();
        for (var i = 0; i < newEntries.length; i++) {
          var entry = newEntries[i];
          var size = entry.transferSize || entry.encodedBodySize || entry.decodedBodySize || 0;
          addResource(entry.name, null, size, entry.initiatorType);
        }
      });

      try {
        performanceObserver.observe({ type: 'resource', buffered: true });
      } catch (e) {
        performanceObserver.observe({ type: 'resource' });
      }
    } catch (e) {
      console.warn('Resource Detector: PerformanceObserver error', e);
    }
  }

  function extractUrlFromCss(value) {
    var match = value.match(/url\(\s*["']?([^"')]+)["']?\s*\)/);
    return match ? match[1] : null;
  }

  function extractUrlsFromCss(cssText) {
    var urls = [];
    var regex = /url\(\s*["']?([^"')]+)["']?\s*\)/g;
    var match;
    while ((match = regex.exec(cssText)) !== null) {
      if (match[1] && !match[1].startsWith('data:')) {
        urls.push(match[1]);
      }
    }
    return urls;
  }

  function scanDomElements() {
    var els;

    els = document.querySelectorAll('img[src]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src, 'img', 0, 'img');
      if (els[i].srcset) {
        var srcsetParts = els[i].srcset.split(',');
        for (var j = 0; j < srcsetParts.length; j++) {
          var srcUrl = srcsetParts[j].trim().split(' ')[0];
          if (srcUrl) addResource(srcUrl, 'img', 0, 'img');
        }
      }
    }

    els = document.querySelectorAll('script[src]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src, 'script', 0, 'script');
    }

    els = document.querySelectorAll('link[href]');
    for (var i = 0; i < els.length; i++) {
      var rel = els[i].rel;
      if (rel === 'stylesheet') addResource(els[i].href, 'stylesheet', 0, 'link');
      else if (rel.indexOf('icon') !== -1) addResource(els[i].href, 'img', 0, 'img');
      else if (rel === 'preload' || rel === 'prefetch' || rel === 'modulepreload' || rel === 'dns-prefetch' || rel === 'manifest')
        addResource(els[i].href, 'other', 0, 'link');
      else addResource(els[i].href, 'other', 0, 'link');
    }

    els = document.querySelectorAll('video[src]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src, 'video', 0, 'video');
      if (els[i].poster) addResource(els[i].poster, 'img', 0, 'img');
    }

    els = document.querySelectorAll('video > source[src], video > source[srcset]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src || els[i].srcset, 'video', 0, 'video');
    }

    els = document.querySelectorAll('audio[src]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src, 'audio', 0, 'audio');
    }

    els = document.querySelectorAll('audio > source[src]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src, 'audio', 0, 'audio');
    }

    els = document.querySelectorAll('iframe[src]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src, 'document', 0, 'iframe');
    }

    els = document.querySelectorAll('object[data]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].data, 'other', 0, 'object');
    }

    els = document.querySelectorAll('embed[src]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src, 'other', 0, 'embed');
    }

    els = document.querySelectorAll('input[type="image"][src]');
    for (var i = 0; i < els.length; i++) {
      addResource(els[i].src, 'img', 0, 'img');
    }

    els = document.querySelectorAll('[style]');
    for (var i = 0; i < els.length; i++) {
      var styleAttr = els[i].getAttribute('style');
      var urls = extractUrlsFromCss(styleAttr);
      for (var j = 0; j < urls.length; j++) {
        addResource(urls[j], 'img', 0, 'img');
      }
    }

    els = document.querySelectorAll('source[srcset]');
    for (var i = 0; i < els.length; i++) {
      var parts = els[i].srcset.split(',');
      var parentIsVideo = els[i].closest('video') !== null;
      for (var j = 0; j < parts.length; j++) {
        var url = parts[j].trim().split(' ')[0];
        if (url) addResource(url, parentIsVideo ? 'video' : 'img', 0, 'source');
      }
    }
  }

  function scanCssResources() {
    try {
      var styleSheets = document.styleSheets;
      for (var i = 0; i < styleSheets.length; i++) {
        try {
          var rules = styleSheets[i].cssRules || styleSheets[i].rules;
          if (!rules) continue;
          for (var j = 0; j < rules.length; j++) {
            var cssText = rules[j].cssText || '';
            var urls = extractUrlsFromCss(cssText);
            for (var k = 0; k < urls.length; k++) {
              try {
                var baseUrl = styleSheets[i].href || window.location.href;
                var absoluteUrl = new URL(urls[k], baseUrl).href;
                addResource(absoluteUrl, 'other', 0, 'css');
              } catch (e) {}
            }
          }
        } catch (e) {
          // cross-origin stylesheet
          continue;
        }
      }
    } catch (e) {}
  }

  function checkElement(el) {
    var tag = el.tagName;
    var styleAttr;
    var urls, j;

    if (tag === 'IMG' && el.src) addResource(el.src, 'img', 0, 'img');
    else if (tag === 'SCRIPT' && el.src) addResource(el.src, 'script', 0, 'script');
    else if (tag === 'LINK' && el.href) {
      if (el.rel === 'stylesheet') addResource(el.href, 'stylesheet', 0, 'link');
      else if (el.rel && el.rel.indexOf('icon') !== -1) addResource(el.href, 'img', 0, 'img');
      else addResource(el.href, 'other', 0, 'link');
    }
    else if (tag === 'VIDEO') {
      if (el.src) addResource(el.src, 'video', 0, 'video');
      if (el.poster) addResource(el.poster, 'img', 0, 'img');
    }
    else if (tag === 'AUDIO' && el.src) addResource(el.src, 'audio', 0, 'audio');
    else if (tag === 'SOURCE' && (el.src || el.srcset)) addResource(el.src || el.srcset, 'other', 0, 'source');
    else if (tag === 'IFRAME' && el.src) addResource(el.src, 'document', 0, 'iframe');
    else if (tag === 'OBJECT' && el.data) addResource(el.data, 'other', 0, 'object');
    else if (tag === 'EMBED' && el.src) addResource(el.src, 'other', 0, 'embed');
    else if (tag === 'INPUT' && el.type === 'image' && el.src) addResource(el.src, 'img', 0, 'img');

    if (el.hasAttribute && el.hasAttribute('style')) {
      styleAttr = el.getAttribute('style');
      urls = extractUrlsFromCss(styleAttr);
      for (j = 0; j < urls.length; j++) {
        addResource(urls[j], 'img', 0, 'img');
      }
    }
  }

  function setupMutationObserver() {
    mutationObserver = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var addedNodes = mutations[i].addedNodes;
        for (var j = 0; j < addedNodes.length; j++) {
          var node = addedNodes[j];
          if (node.nodeType !== 1) continue;

          checkElement(node);

          if (node.querySelectorAll) {
            var children = node.querySelectorAll('img[src], script[src], link[href], video[src], video[poster], audio[src], source[src], source[srcset], iframe[src], object[data], embed[src], input[type="image"][src], [style]');
            for (var k = 0; k < children.length; k++) {
              checkElement(children[k]);
            }
          }
        }
      }
    });

    mutationObserver.observe(document.documentElement, {
      childList: true,
      subtree: true
    });
  }

  function initialize() {
    if (initialized) return;
    initialized = true;

    setupPerformanceObserver();

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

  function getTypeCounts(resourceArray) {
    var counts = {};
    for (var i = 0; i < resourceArray.length; i++) {
      var type = resourceArray[i].type;
      counts[type] = (counts[type] || 0) + 1;
    }
    return counts;
  }

  chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    if (message.action === 'getResources') {
      scanDomElements();
      scanCssResources();

      var resourceArray = [];
      var entries = resources.values();
      var entry = entries.next();
      while (!entry.done) {
        resourceArray.push(entry.value);
        entry = entries.next();
      }

      resourceArray.sort(function (a, b) {
        if (a.type !== b.type) return a.type.localeCompare(b.type);
        return a.filename.localeCompare(b.filename);
      });

      sendResponse({
        resources: resourceArray,
        total: resourceArray.length,
        types: getTypeCounts(resourceArray)
      });
      return true;
    }

    if (message.action === 'ping') {
      sendResponse({ pong: true, ready: initialized });
      return false;
    }
  });

  initialize();
})();
