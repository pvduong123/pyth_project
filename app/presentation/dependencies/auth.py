from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.auth_service import AuthService
from app.application.billing_service import BillingService
from app.application.password_reset_service import PasswordResetService
from app.application.profile_service import ProfileService
from app.core.config import Settings, get_settings
from app.domain.entities.user import User
from app.infrastructure.database.session import get_db_session
from app.infrastructure.notifications.dev_email_service import DevEmailService
from app.infrastructure.repositories.sqlalchemy_billing_profile_repository import (
    SqlAlchemyBillingProfileRepository,
)
from app.infrastructure.repositories.sqlalchemy_password_reset_token_repository import (
    SqlAlchemyPasswordResetTokenRepository,
)
from app.infrastructure.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository
from app.infrastructure.security.jwt_tokens import JwtTokenService
from app.infrastructure.security.password import PwdlibPasswordHasher
from app.infrastructure.security.reset_tokens import SecureResetTokenService


def get_auth_service(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        user_repository=SqlAlchemyUserRepository(db_session),
        password_hasher=PwdlibPasswordHasher(),
        auth_token_service=JwtTokenService(
            secret_key=settings.secret_key,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_expire_minutes,
        ),
    )


def get_profile_service(db_session: Session = Depends(get_db_session)) -> ProfileService:
    return ProfileService(user_repository=SqlAlchemyUserRepository(db_session))


def get_billing_service(db_session: Session = Depends(get_db_session)) -> BillingService:
    return BillingService(billing_repository=SqlAlchemyBillingProfileRepository(db_session))


def get_password_reset_service(
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> PasswordResetService:
    return PasswordResetService(
        user_repository=SqlAlchemyUserRepository(db_session),
        token_repository=SqlAlchemyPasswordResetTokenRepository(db_session),
        password_hasher=PwdlibPasswordHasher(),
        reset_token_service=SecureResetTokenService(),
        email_service=DevEmailService(),
        reset_token_expire_minutes=settings.reset_token_expire_minutes,
    )


def get_optional_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> User | None:
    raw_token = request.cookies.get(settings.cookie_name)
    return auth_service.get_user_by_access_token(raw_token)


def get_current_user_for_api(user: User | None = Depends(get_optional_current_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user
