(function () {
  const BLOCK_TAGS = new Set([
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'pre', 'blockquote', 'hr',
    'ul', 'ol', 'li',
    'table', 'thead', 'tbody', 'tfoot', 'tr',
    'div', 'section', 'article', 'aside',
    'header', 'footer', 'main', 'nav',
    'figure', 'figcaption', 'details', 'summary',
    'form', 'fieldset', 'dl', 'dt', 'dd'
  ]);

  const SKIP_TAGS = new Set([
    'script', 'style', 'noscript', 'iframe', 'object',
    'embed', 'canvas', 'svg', 'video', 'audio',
    'template', 'link', 'meta', 'input', 'button',
    'select', 'textarea', 'option', 'optgroup',
    'datalist', 'output', 'progress', 'meter'
  ]);

  const NON_CONTENT_SELECTORS = [
    'script', 'style', 'noscript', 'iframe', 'object', 'embed',
    'nav[role="navigation"]', 'footer[role="contentinfo"]',
    '[aria-hidden="true"]',
    '.sidebar', '.nav', '.navigation', '.menu',
    '.advertisement', '.ads', '.ad',
    '.social-share', '.comments', '.comment',
    'template'
  ];

  function resolveUrl(href) {
    if (!href) return '';
    href = href.trim();
    if (!href) return '';
    if (/^(https?:|mailto:|tel:|#|javascript:)/i.test(href)) return href;
    try {
      return new URL(href, window.location.href).href;
    } catch (e) {
      return href;
    }
  }

  function isHidden(node) {
    if (node.nodeType !== Node.ELEMENT_NODE) return false;
    const style = window.getComputedStyle(node);
    if (style.display === 'none' || style.visibility === 'hidden') return true;
    if (parseFloat(style.opacity) === 0) return true;
    return false;
  }

  function findMainContent(root) {
    const selectors = [
      'article',
      'main',
      '[role="main"]',
      '.post-content', '.article-content', '.entry-content',
      '#content', '.content',
      '.markdown-body', '.prose'
    ];
    for (const sel of selectors) {
      const el = root.querySelector(sel);
      if (el && el.textContent.trim().length > 100) return el;
    }
    return root;
  }

  function removeUnwanted(root) {
    const clones = [];
    NON_CONTENT_SELECTORS.forEach(sel => {
      root.querySelectorAll(sel).forEach(el => {
        if (!el.closest('article, main, [role="main"]')) {
          el.remove();
        }
      });
    });
  }

  function cleanWhitespace(md) {
    return md
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .replace(/[ \t]+$/gm, '')
      .replace(/^\n+/, '')
      .replace(/\n+$/, '\n')
      .replace(/[ \t]+\n/g, '\n')
      .replace(/^[ \t]+$/gm, '')
      .replace(/\n\n\n+/g, '\n\n');
  }

  function isBlockTag(tag) {
    return BLOCK_TAGS.has(tag);
  }

  function getListDepth(node) {
    let depth = 0;
    let parent = node.parentElement;
    while (parent) {
      const tag = parent.tagName.toLowerCase();
      if (tag === 'ul' || tag === 'ol') depth++;
      parent = parent.parentElement;
    }
    return depth;
  }

  function getOrderedIndex(node) {
    let idx = 0;
    let sibling = node;
    while ((sibling = sibling.previousElementSibling)) {
      if (sibling.tagName.toLowerCase() === 'li') idx++;
    }
    return idx + 1;
  }

  function convertTable(table) {
    const rows = [];
    table.querySelectorAll('tr').forEach(row => {
      rows.push(row);
    });
    if (rows.length === 0) return '';

    const cellData = [];
    let maxCols = 0;

    rows.forEach(row => {
      const cells = row.querySelectorAll('td, th');
      maxCols = Math.max(maxCols, cells.length);
    });

    rows.forEach(row => {
      const cells = row.querySelectorAll('td, th');
      const rowData = [];
      let colIdx = 0;

      cells.forEach(cell => {
        const content = processInline(cell).replace(/\|/g, '\\|').replace(/\n/g, ' ').trim();
        const colspan = Math.max(1, parseInt(cell.getAttribute('colspan') || '1'));
        for (let i = 0; i < colspan && colIdx < maxCols; i++) {
          rowData[colIdx++] = content;
        }
      });

      while (colIdx < maxCols) {
        rowData[colIdx++] = '';
      }
      cellData.push(rowData);
    });

    let result = '';
    const hasHeader = rows[0] && rows[0].querySelectorAll('th').length > 0;

    cellData.forEach((rowData, idx) => {
      result += '| ' + rowData.join(' | ') + ' |\n';
      if (idx === 0 && hasHeader) {
        result += '| ' + rowData.map(() => '---').join(' | ') + ' |\n';
      }
    });

    return result;
  }

  function processInline(node) {
    if (!node) return '';
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    if (isHidden(node)) return '';
    if (SKIP_TAGS.has(node.tagName.toLowerCase())) return '';

    const tag = node.tagName.toLowerCase();
    let content = '';
    for (const child of node.childNodes) {
      content += processInline(child);
    }

    switch (tag) {
      case 'br': return '\n';
      case 'b': case 'strong': return '**' + content + '**';
      case 'i': case 'em': return '*' + content + '*';
      case 's': case 'strike': case 'del': return '~~' + content + '~~';
      case 'u': case 'ins': return content;
      case 'code': return '`' + content + '`';
      case 'kbd': return '`' + content + '`';
      case 'mark': return '==' + content + '==';
      case 'sub': return '~' + content + '~';
      case 'sup': return '^' + content + '^';
      case 'small': return content;
      case 'a': {
        const href = resolveUrl(node.getAttribute('href'));
        if (href && href !== '#') return '[' + content.trim() + '](' + href + ')';
        return content;
      }
      case 'img': {
        const src = resolveUrl(node.getAttribute('src'));
        const alt = node.getAttribute('alt') || '';
        if (src) return '![' + alt + '](' + src + ')';
        return '';
      }
      case 'abbr': {
        const title = node.getAttribute('title');
        if (title) return content + ' (' + title + ')';
        return content;
      }
      case 'span': case 'label': case 'time': case 'cite':
      case 'q': case 'var': case 'samp': case 'dfn':
        return content;
      default: return content;
    }
  }

  function convertElement(node) {
    if (!node) return '';
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    if (isHidden(node)) return '';

    const tag = node.tagName.toLowerCase();
    if (SKIP_TAGS.has(tag)) return '';

    // Process children
    let content = '';
    for (const child of node.childNodes) {
      content += convertElement(child);
    }

    switch (tag) {
      case 'h1': return '\n\n# ' + processInline(node) + '\n\n';
      case 'h2': return '\n\n## ' + processInline(node) + '\n\n';
      case 'h3': return '\n\n### ' + processInline(node) + '\n\n';
      case 'h4': return '\n\n#### ' + processInline(node) + '\n\n';
      case 'h5': return '\n\n##### ' + processInline(node) + '\n\n';
      case 'h6': return '\n\n###### ' + processInline(node) + '\n\n';

      case 'p':
        return '\n\n' + processInline(node) + '\n\n';

      case 'br':
        return '\n';

      case 'hr':
        return '\n\n---\n\n';

      case 'pre': {
        const codeEl = node.querySelector('code');
        let codeText = codeEl ? codeEl.textContent : node.textContent;
        let lang = '';
        if (codeEl) {
          const match = codeEl.className.match(/language-(\w+)/);
          if (match) lang = match[1];
        }
        return '\n\n```' + lang + '\n' + codeText.trim() + '\n```\n\n';
      }

      case 'blockquote': {
        const lines = content.trim().split('\n');
        return '\n\n' + lines.map(line => '> ' + line).join('\n') + '\n\n';
      }

      case 'ul':
      case 'ol':
        return '\n\n' + content + '\n';

      case 'li': {
        const parentTag = node.parentElement ? node.parentElement.tagName.toLowerCase() : 'ul';
        const depth = getListDepth(node);
        const indent = '  '.repeat(Math.max(0, depth - 1));
        const prefix = parentTag === 'ol' ? getOrderedIndex(node) + '. ' : '- ';
        const inlineContent = processInline(node).trim();
        if (!inlineContent) {
          const subContent = content.trim();
          if (subContent) {
            const subLines = subContent.split('\n').filter(l => l.trim());
            return '\n' + indent + prefix + subLines[0].replace(/^[-*]\s+/, '') + '\n' +
              subLines.slice(1).map(l => '  ' + indent + l).join('\n') + '\n';
          }
          return '\n' + indent + prefix + '\n';
        }
        const subContent = content.replace(inlineContent, '').trim();
        if (subContent) {
          const subLines = subContent.split('\n').filter(l => l.trim());
          return '\n' + indent + prefix + inlineContent + '\n' +
            subLines.map(l => '  ' + indent + l).join('\n') + '\n';
        }
        return '\n' + indent + prefix + inlineContent + '\n';
      }

      case 'dl':
        return '\n\n' + content + '\n';

      case 'dt':
        return '\n**' + processInline(node).trim() + '**\n';

      case 'dd':
        return '\n: ' + processInline(node).trim() + '\n';

      case 'table': {
        const tableContent = convertTable(node);
        return '\n\n' + tableContent + '\n\n';
      }

      case 'thead': case 'tbody': case 'tfoot':
        return content;

      case 'tr': {
        return content + '\n';
      }

      case 'th': case 'td': {
        return processInline(node);
      }

      case 'figure': {
        const img = node.querySelector('img');
        const caption = node.querySelector('figcaption');
        let result = '';
        if (img) {
          result += convertElement(img);
        }
        if (caption) {
          result += '\n*' + caption.textContent.trim() + '*\n';
        }
        return '\n\n' + result.trim() + '\n\n';
      }

      case 'details': {
        const summary = node.querySelector('summary');
        let result = '\n\n';
        if (summary) {
          result += '**' + summary.textContent.trim() + '**\n\n';
          summary.remove();
        }
        result += content.trim() + '\n\n';
        return result;
      }

      case 'summary':
      case 'a':
      case 'strong': case 'b':
      case 'em': case 'i':
      case 'code':
      case 'del': case 's': case 'strike':
      case 'img':
      case 'sub': case 'sup':
      case 'mark': case 'kbd':
      case 'u': case 'ins':
      case 'span': case 'label': case 'time':
        return processInline(node);

      case 'div': case 'section': case 'article': case 'aside':
      case 'header': case 'footer': case 'main': case 'nav':
        return '\n\n' + content.trim() + '\n\n';

      default:
        if (isBlockTag(tag)) {
          return '\n\n' + content.trim() + '\n\n';
        }
        return content;
    }
  }

  window.html2md = function (rootElement) {
    if (!rootElement) return '';

    const main = findMainContent(rootElement);

    // Clone to avoid modifying the live DOM
    const clone = main.cloneNode(true);
    removeUnwanted(clone);

    let md = convertElement(clone);
    md = cleanWhitespace(md);
    return md;
  };
})();
