class ApplicationError(Exception):
    """Base application error."""


class InvalidCredentialsError(ApplicationError):
    """Raised when authentication fails."""


class DuplicateEmailError(ApplicationError):
    """Raised when a user with the same email already exists."""


class ValidationError(ApplicationError):
    """Raised when user-provided data is invalid."""


class InvalidResetTokenError(ApplicationError):
    """Raised when a password reset token is invalid or expired."""
