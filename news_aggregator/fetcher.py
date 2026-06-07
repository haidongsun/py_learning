import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import feedparser
import requests

from .config import REQUEST_TIMEOUT, USER_AGENT, MAX_ITEMS_PER_FEED

logger = logging.getLogger(__name__)


def _fetch_single(url: str) -> list[dict]:
    headers = {'User-Agent': USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)

    items = []
    for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
        item = {
            'title': getattr(entry, 'title', '').strip(),
            'link': getattr(entry, 'link', ''),
            'summary': _clean_summary(getattr(entry, 'summary', '')),
            'published': _parse_date(entry),
            'source': getattr(feed.feed, 'title', url),
            'source_url': url,
        }
        items.append(item)
    return items


def _clean_summary(text: str) -> str:
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300]


def _parse_date(entry) -> str:
    from time import mktime
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            return datetime.fromtimestamp(mktime(entry.published_parsed)).strftime('%Y-%m-%d %H:%M')
        except Exception:
            pass
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        try:
            return datetime.fromtimestamp(mktime(entry.updated_parsed)).strftime('%Y-%m-%d %H:%M')
        except Exception:
            pass
    return datetime.now().strftime('%Y-%m-%d %H:%M')


def fetch_all(feeds: dict[str, list[str]]) -> dict[str, list[dict]]:
    all_items: dict[str, list[dict]] = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {}
        for category, urls in feeds.items():
            for url in urls:
                future = executor.submit(_fetch_single, url)
                future_to_url[future] = (category, url)

        for future in as_completed(future_to_url):
            category, url = future_to_url[future]
            try:
                items = future.result()
                all_items.setdefault(category, []).extend(items)
                logger.info(f'Fetched {len(items)} items from {url}')
            except Exception as e:
                logger.warning(f'Failed to fetch {url}: {e}')

    return all_items
