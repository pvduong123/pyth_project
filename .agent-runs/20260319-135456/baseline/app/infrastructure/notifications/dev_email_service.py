import logging

from app.domain.services.email_service import EmailService


logger = logging.getLogger(__name__)


class DevEmailService(EmailService):
    def send_password_reset(self, email: str, reset_link: str) -> None:
        logger.warning("Password reset requested for %s. Reset link: %s", email, reset_link)
