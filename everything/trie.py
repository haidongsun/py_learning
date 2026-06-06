class TrieNode:
    __slots__ = ('children', 'is_end', 'values')

    def __init__(self):
        self.children = {}
        self.is_end = False
        self.values = []


class Trie:
    """Compact prefix tree for fast prefix-based path lookup."""

    def __init__(self):
        self.root = TrieNode()
        self._size = 0

    def insert(self, key: str, value: str):
        node = self.root
        for ch in key:
            node = node.children.setdefault(ch, TrieNode())
        if not node.is_end:
            node.is_end = True
        node.values.append(value)
        self._size += 1

    def _collect(self, node, results, limit):
        if len(results) >= limit:
            return
        if node.is_end:
            results.extend(node.values[: limit - len(results)])
        for child in node.children.values():
            if len(results) >= limit:
                return
            self._collect(child, results, limit)

    def search_prefix(self, prefix: str, limit: int = 1000):
        node = self.root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return []
        results = []
        self._collect(node, results, limit)
        return results

    def remove(self, key: str, value: str):
        node = self.root
        path = [self.root]
        for ch in key:
            if ch not in node.children:
                return False
            node = node.children[ch]
            path.append(node)
        if value not in node.values:
            return False
        node.values.remove(value)
        if not node.values:
            node.is_end = False
        self._size -= 1
        return True

    def __len__(self):
        return self._size
