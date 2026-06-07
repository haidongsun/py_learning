import logging
import os
import sys
from datetime import datetime

from .config import CATEGORIES
from .fetcher import fetch_all
from .organizer import deduplicate
from .output import write_markdown, write_html

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def run():
    logger.info('News Aggregator started - ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    feeds = {cat: cfg['feeds'] for cat, cfg in CATEGORIES.items()}
    logger.info(f'Fetching from {sum(len(v) for v in feeds.values())} feeds across {len(feeds)} categories...')

    raw_items = fetch_all(feeds)
    items = deduplicate(raw_items)

    total = 0
    for cat, entries in items.items():
        logger.info(f'  {cat}: {len(entries)} items')
        total += len(entries)

    if total == 0:
        logger.warning('No news items fetched.')
        sys.exit(1)

    md_path = write_markdown(items)
    html_path = write_html(items)

    logger.info(f'Done. {total} news items saved.')
    out_dir = os.path.dirname(md_path)
    print(f'Output: {out_dir}')
    print(f'  Markdown: news_{datetime.now().strftime("%Y-%m-%d")}.md')
    print(f'  HTML:     news_{datetime.now().strftime("%Y-%m-%d")}.html')


if __name__ == '__main__':
    run()
