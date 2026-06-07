import logging

logger = logging.getLogger(__name__)


def deduplicate(all_items: dict[str, list[dict]]) -> dict[str, list[dict]]:
    seen_titles: set[str] = set()
    result: dict[str, list[dict]] = {}

    for category, items in all_items.items():
        unique = []
        for item in items:
            key = _normalize(item['title'])
            if key and key not in seen_titles:
                seen_titles.add(key)
                unique.append(item)
        result[category] = unique
        logger.info(f'{category}: {len(unique)} unique items (from {len(items)} raw)')

    return result


def _normalize(title: str) -> str:
    return title.lower().strip().rstrip('.!?；。！？')
