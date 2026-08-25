"""AI-specific exceptions mapped to user-friendly API errors."""

from app.core.exceptions import AppError


class AIConfigError(AppError):
    def __init__(self, message: str = "AI service is not configured.") -> None:
        super().__init__(message=message, code="ai_not_configured", status_code=503)


class AIProviderError(AppError):
    def __init__(self, message: str = "AI service is temporarily unavailable.") -> None:
        super().__init__(message=message, code="ai_provider_error", status_code=502)


class AITimeoutError(AppError):
    def __init__(self, message: str = "AI analysis timed out. Please try again.") -> None:
        super().__init__(message=message, code="ai_timeout", status_code=504)


class AIRateLimitError(AppError):
    def __init__(self, message: str = "AI service rate limit reached. Please try again shortly.") -> None:
        super().__init__(message=message, code="ai_rate_limit", status_code=429)


class AIOutputValidationError(AppError):
    def __init__(
        self,
        message: str = "AI returned an invalid analysis. Please try again.",
    ) -> None:
        super().__init__(message=message, code="ai_output_invalid", status_code=502)
