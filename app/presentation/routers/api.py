from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import OperationalError

from app.application.auth_service import AuthService
from app.application.errors import (
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidResetTokenError,
    ValidationError,
)
from app.application.password_reset_service import PasswordResetService
from app.core.config import Settings, get_settings
from app.domain.entities.user import User
from app.presentation.dependencies.auth import (
    get_auth_service,
    get_current_user_for_api,
    get_password_reset_service,
)
from app.presentation.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    UserResponse,
)


router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: AuthRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    try:
        user = auth_service.register_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except (DuplicateEmailError, ValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/auth/login", response_model=UserResponse)
def login(
    payload: AuthLoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> UserResponse:
    try:
        user = auth_service.authenticate(email=payload.email, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    raw_token = auth_service.create_access_token(user_id=user.id)
    response.set_cookie(
        key=settings.cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> Response:
    response.delete_cookie(settings.cookie_name)
    return response


@router.get("/auth/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user_for_api)) -> UserResponse:
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/auth/forgot-password", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> MessageResponse:
    try:
        password_reset_service.request_password_reset(
            email=payload.email,
            reset_link_base_url=str(request.base_url).rstrip("/"),
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable. Start PostgreSQL and try again.",
        ) from exc
    return MessageResponse(message="If the account exists, a password reset link has been sent.")


@router.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    response: Response,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    try:
        password_reset_service.reset_password(raw_token=payload.token, new_password=payload.password)
    except (InvalidResetTokenError, ValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    response.delete_cookie(settings.cookie_name)
    return MessageResponse(message="Password reset successful. Please sign in again.")
