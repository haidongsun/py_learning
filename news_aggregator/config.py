import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resource', 'news_output')

CATEGORIES = {
    '科技资讯': {
        'icon': '💻',
        'feeds': [
            'https://36kr.com/feed',
            'https://www.ithome.com/rss/',
            'https://rss.huxiu.com/',
            'https://www.ifanr.com/feed',
            'https://www.tmtpost.com/feed',
            'https://www.solidot.org/index.rss',
            'https://www.leiphone.com/feed',
        ],
    },
    '开发者': {
        'icon': '⌨️',
        'feeds': [
            'https://www.oschina.net/news/rss',
            'https://segmentfault.com/feeds',
            'https://juejin.cn/rss',
            'https://www.infoq.cn/feed',
            'https://sspai.com/feed',
            'https://www.landiannews.com/feed',
        ],
    },
    '财经': {
        'icon': '💰',
        'feeds': [
            'https://feeds.content.dowjones.io/public/rss/mw_topstories',
            'https://www.cnbc.com/id/100003114/device/rss/rss.html',
        ],
    },
}

REQUEST_TIMEOUT = 20
USER_AGENT = 'NewsAggregator/1.0 (Python)'
MAX_ITEMS_PER_FEED = 20
OUTPUT_FORMATS = ['md', 'html']
