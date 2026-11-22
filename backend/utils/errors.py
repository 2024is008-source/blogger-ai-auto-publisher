"""Typed error hierarchy for structured, recoverable error handling."""

from __future__ import annotations


class AppError(Exception):
    """Base application error with machine-readable code and retry hint."""

    def __init__(self, message: str, *, code: str = "APP_ERROR", retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ConfigurationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFIGURATION_ERROR", retryable=False)


class GeminiAPIError(AppError):
    def __init__(self, message: str, *, code: str = "GEMINI_API_ERROR", retryable: bool = False) -> None:
        super().__init__(message, code=code, retryable=retryable)


class GeminiQuotaError(GeminiAPIError):
    def __init__(self, message: str = "Gemini API quota exceeded or rate-limited.") -> None:
        super().__init__(message, code="GEMINI_QUOTA_EXCEEDED", retryable=True)


class ImageProviderError(AppError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message, code="IMAGE_PROVIDER_ERROR", retryable=retryable)


class InvalidLicenseError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_IMAGE_LICENSE", retryable=False)


class ImageUploadConfigError(ConfigurationError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "IMAGE_UPLOAD_NOT_CONFIGURED"


class BloggerAuthError(AppError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message, code="BLOGGER_AUTH_ERROR", retryable=retryable)


class BloggerAPIError(AppError):
    def __init__(self, message: str, *, code: str = "BLOGGER_API_ERROR", retryable: bool = False) -> None:
        super().__init__(message, code=code, retryable=retryable)


class BloggerQuotaError(BloggerAPIError):
    def __init__(self, message: str = "Blogger API quota exceeded.") -> None:
        super().__init__(message, code="BLOGGER_QUOTA_EXCEEDED", retryable=True)


class DuplicateArticleError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="DUPLICATE_ARTICLE", retryable=False)


class InvalidScheduleError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_SCHEDULE_TIME", retryable=False)


class StorageError(AppError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message, code="STORAGE_ERROR", retryable=retryable)
