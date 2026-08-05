from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import httpx


class ErrorCode(StrEnum):
    TRANSIENT_NETWORK = "transient_network"
    PARSE_ERROR = "parse_error"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"
    PERMANENT = "permanent"


@dataclass(frozen=True, slots=True)
class ErrorDecision:
    code: ErrorCode
    retryable: bool
    max_attempts: int


class ErrorClassifier:
    def classify(
        self, error: BaseException | None = None, http_status: int | None = None
    ) -> ErrorDecision:
        if http_status == 429:
            return ErrorDecision(ErrorCode.RATE_LIMITED, True, 3)
        if http_status in {401, 403}:
            return ErrorDecision(ErrorCode.BLOCKED, False, 1)
        if http_status is not None and 500 <= http_status <= 599:
            return ErrorDecision(ErrorCode.TRANSIENT_NETWORK, True, 3)
        if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
            return ErrorDecision(ErrorCode.TRANSIENT_NETWORK, True, 3)
        if isinstance(error, (UnicodeError, ValueError)):
            return ErrorDecision(ErrorCode.PARSE_ERROR, False, 1)
        return ErrorDecision(ErrorCode.PERMANENT, False, 1)
