from abc import ABC, abstractmethod
from typing import Any


class PaginationStrategy(ABC):
    @abstractmethod
    def get_next_params(
        self, current_response: dict[str, Any], current_params: dict[str, Any]
    ) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def extract_items(self, response: dict[str, Any]) -> list[Any]:
        pass

    @abstractmethod
    def has_more_pages(self, response: dict[str, Any]) -> bool:
        pass


class CursorPagination(PaginationStrategy):
    def __init__(
        self,
        cursor_response_key: str,
        cursor_request_param: str,
        items_key: str,
        max_results_param: str | None = None,
        default_page_size: int = 100,
    ):
        self.cursor_response_key = cursor_response_key
        self.cursor_request_param = cursor_request_param
        self.items_key = items_key
        self.max_results_param = max_results_param
        self.default_page_size = default_page_size

    def get_next_params(
        self, current_response: dict[str, Any], current_params: dict[str, Any]
    ) -> dict[str, Any] | None:
        next_cursor = current_response.get(self.cursor_response_key)
        if not next_cursor:
            return None

        next_params = current_params.copy()
        next_params[self.cursor_request_param] = next_cursor
        return next_params

    def extract_items(self, response: dict[str, Any]) -> list[Any]:
        return response.get(self.items_key, [])

    def has_more_pages(self, response: dict[str, Any]) -> bool:
        return bool(response.get(self.cursor_response_key))

    def get_initial_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.max_results_param:
            params[self.max_results_param] = self.default_page_size
        return params


class OffsetPagination(PaginationStrategy):
    def __init__(
        self,
        offset_param: str,
        limit_param: str,
        items_key: str,
        total_key: str | None = None,
        default_limit: int = 100,
    ):
        self.offset_param = offset_param
        self.limit_param = limit_param
        self.items_key = items_key
        self.total_key = total_key
        self.default_limit = default_limit
        self._current_offset = 0

    def get_next_params(
        self, current_response: dict[str, Any], current_params: dict[str, Any]
    ) -> dict[str, Any] | None:
        items = self.extract_items(current_response)
        limit = current_params.get(self.limit_param, self.default_limit)

        if len(items) < limit:
            return None

        if self.total_key:
            total = current_response.get(self.total_key, 0)
            current_offset = current_params.get(self.offset_param, 0)
            if current_offset + limit >= total:
                return None

        next_params = current_params.copy()
        next_params[self.offset_param] = (
            current_params.get(self.offset_param, 0) + limit
        )
        return next_params

    def extract_items(self, response: dict[str, Any]) -> list[Any]:
        return response.get(self.items_key, [])

    def has_more_pages(self, response: dict[str, Any]) -> bool:
        items = self.extract_items(response)
        return len(items) >= self.default_limit

    def get_initial_params(self) -> dict[str, Any]:
        return {
            self.offset_param: 0,
            self.limit_param: self.default_limit,
        }


class NoPagination(PaginationStrategy):
    def __init__(self, items_key: str):
        self.items_key = items_key

    def get_next_params(
        self, current_response: dict[str, Any], current_params: dict[str, Any]
    ) -> dict[str, Any] | None:
        return None

    def extract_items(self, response: dict[str, Any]) -> list[Any]:
        return response.get(self.items_key, [])

    def has_more_pages(self, response: dict[str, Any]) -> bool:
        return False
