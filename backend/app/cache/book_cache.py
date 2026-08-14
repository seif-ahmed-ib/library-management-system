from typing import Any

from app.cache.redis_cache import CacheLookup, redis_cache


class BookCache:
    LIST_KEY_PREFIX = "library:books:list"
    ITEM_KEY_PREFIX = "library:books:item"

    @staticmethod
    def _list_key(skip: int, limit: int) -> str:
        return f"{BookCache.LIST_KEY_PREFIX}:{skip}:{limit}"

    @staticmethod
    def _item_key(book_id: int) -> str:
        return f"{BookCache.ITEM_KEY_PREFIX}:{book_id}"

    def get_list(self, skip: int, limit: int) -> CacheLookup:
        return redis_cache.get_json(self._list_key(skip, limit))

    def set_list(
        self,
        skip: int,
        limit: int,
        books: list[dict[str, Any]],
    ) -> bool:
        return redis_cache.set_json(
            self._list_key(skip, limit),
            books,
        )

    def get_item(self, book_id: int) -> CacheLookup:
        return redis_cache.get_json(self._item_key(book_id))

    def set_item(
        self,
        book_id: int,
        book: dict[str, Any],
    ) -> bool:
        return redis_cache.set_json(
            self._item_key(book_id),
            book,
        )

    def invalidate(self, book_id: int | None = None) -> None:
        redis_cache.delete_pattern(f"{self.LIST_KEY_PREFIX}:*")

        if book_id is not None:
            redis_cache.delete(self._item_key(book_id))


book_cache = BookCache()
