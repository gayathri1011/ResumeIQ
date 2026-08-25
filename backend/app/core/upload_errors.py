"""Custom application errors for resume upload and parsing."""

from app.core.exceptions import AppError


class InvalidFileTypeError(AppError):
    def __init__(
        self,
        message: str = "Only PDF, DOCX, and image files (PNG, JPG, WEBP) are supported.",
    ) -> None:
        super().__init__(message=message, code="invalid_file_type", status_code=400)


class FileTooLargeError(AppError):
    def __init__(self, max_mb: int) -> None:
        super().__init__(
            message=f"File exceeds the maximum allowed size of {max_mb} MB.",
            code="file_too_large",
            status_code=413,
        )


class CorruptedFileError(AppError):
    def __init__(self, message: str = "The file appears to be corrupted or unreadable.") -> None:
        super().__init__(message=message, code="corrupted_file", status_code=422)


class EmptyResumeError(AppError):
    def __init__(
        self,
        message: str = "No readable text could be extracted from this resume.",
    ) -> None:
        super().__init__(message=message, code="empty_resume", status_code=422)


class ExtractionFailedError(AppError):
    def __init__(
        self,
        message: str = "We could not extract structured content from this resume.",
    ) -> None:
        super().__init__(message=message, code="extraction_failed", status_code=422)
