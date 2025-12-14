from app.integrations.core.pagination import (
    CursorPagination,
    NoPagination,
    PaginationStrategy,
)
from app.integrations.core.types import SyncStep
from app.integrations.providers.google_workspace.constants import (
    GOOGLE_DEFAULT_PAGE_SIZE,
)


class GoogleUsersPaginator(CursorPagination):
    def __init__(self):
        super().__init__(
            cursor_response_key="nextPageToken",
            cursor_request_param="pageToken",
            items_key="users",
            max_results_param="maxResults",
            default_page_size=GOOGLE_DEFAULT_PAGE_SIZE,
        )


class GoogleGroupsPaginator(CursorPagination):
    def __init__(self):
        super().__init__(
            cursor_response_key="nextPageToken",
            cursor_request_param="pageToken",
            items_key="groups",
            max_results_param="maxResults",
            default_page_size=GOOGLE_DEFAULT_PAGE_SIZE,
        )


class GoogleGroupMembersPaginator(CursorPagination):
    def __init__(self):
        super().__init__(
            cursor_response_key="nextPageToken",
            cursor_request_param="pageToken",
            items_key="members",
            max_results_param="maxResults",
            default_page_size=GOOGLE_DEFAULT_PAGE_SIZE,
        )


class GoogleTokenEventsPaginator(CursorPagination):
    def __init__(self):
        super().__init__(
            cursor_response_key="nextPageToken",
            cursor_request_param="pageToken",
            items_key="items",
            max_results_param="maxResults",
            default_page_size=GOOGLE_DEFAULT_PAGE_SIZE,
        )


class GoogleUserTokensPaginator(CursorPagination):
    def __init__(self):
        super().__init__(
            cursor_response_key="nextPageToken",
            cursor_request_param="pageToken",
            items_key="items",
            max_results_param="maxResults",
            default_page_size=GOOGLE_DEFAULT_PAGE_SIZE,
        )


def get_paginator_for_step(step: SyncStep) -> PaginationStrategy:
    if step == SyncStep.USERS:
        return GoogleUsersPaginator()
    if step == SyncStep.GROUPS:
        return GoogleGroupsPaginator()
    if step == SyncStep.GROUP_MEMBERS:
        return GoogleGroupMembersPaginator()
    if step == SyncStep.TOKEN_EVENTS:
        return GoogleTokenEventsPaginator()
    if step == SyncStep.USER_TOKENS:
        return GoogleUserTokensPaginator()
    return GoogleUsersPaginator()
