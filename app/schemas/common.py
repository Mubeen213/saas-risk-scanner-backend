from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel

T = TypeVar("T")


class MetaResponse(BaseModel):
    request_id: str
    timestamp: datetime


class PaginationResponse(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class ErrorDetail(BaseModel):
    code: str
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    target: str | None = None
    details: list[ErrorDetail] | None = None


class ApiResponse(BaseModel, Generic[T]):
    meta: MetaResponse
    data: T | None = None
    error: ErrorResponse | None = None


def create_success_response[T](data: T) -> ApiResponse[T]:
    return ApiResponse(
        meta=MetaResponse(
            request_id=str(uuid4()),
            timestamp=datetime.utcnow(),
        ),
        data=data,
        error=None,
    )


def create_error_response(
    code: str, message: str, target: str | None = None
) -> ApiResponse[None]:
    return ApiResponse(
        meta=MetaResponse(
            request_id=str(uuid4()),
            timestamp=datetime.utcnow(),
        ),
        data=None,
        error=ErrorResponse(code=code, message=message, target=target),
    )
