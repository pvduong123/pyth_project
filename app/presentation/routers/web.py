from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import OperationalError

from app.application.auth_service import AuthService
from app.application.billing_service import BillingService
from app.application.errors import (
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidResetTokenError,
    ValidationError,
)
from app.application.password_reset_service import PasswordResetService
from app.application.profile_service import ProfileService
from app.core.config import Settings, get_settings
from app.domain.entities.user import User
from app.presentation.dependencies.auth import (
    get_auth_service,
    get_billing_service,
    get_optional_current_user,
    get_password_reset_service,
    get_profile_service,
)


templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)


def redirect_to(path: str, status_code: int = status.HTTP_303_SEE_OTHER) -> RedirectResponse:
    return RedirectResponse(url=path, status_code=status_code)


def render_template(
    request: Request,
    template_name: str,
    settings: Settings,
    current_user: User | None = None,
    status_code: int = status.HTTP_200_OK,
    **context: object,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        status_code=status_code,
        context={
            "app_name": settings.app_name,
            "current_user": current_user,
            **context,
        },
    )


@router.get("/", response_class=HTMLResponse)
def root(
    request: Request,
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    if current_user is not None:
        return redirect_to("/dashboard")
    return render_template(request, "auth/login.html", settings=settings, current_user=None, errors={})


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    if current_user is not None:
        return redirect_to("/dashboard")
    success_message = "Your password has been reset. Please sign in again." if request.query_params.get("reset") == "success" else None
    return render_template(
        request,
        "auth/login.html",
        settings=settings,
        current_user=None,
        errors={},
        success_message=success_message,
    )


@router.post("/login")
def login_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    try:
        user = auth_service.authenticate(email=email, password=password)
    except InvalidCredentialsError as exc:
        return render_template(
            request,
            "auth/login.html",
            settings=settings,
            current_user=None,
            errors={"form": str(exc)},
            values={"email": email},
        )

    raw_token = auth_service.create_access_token(user_id=user.id)
    response = redirect_to("/dashboard")
    response.set_cookie(
        key=settings.cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    if current_user is not None:
        return redirect_to("/dashboard")
    return render_template(request, "auth/register.html", settings=settings, current_user=None, errors={})


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(
    request: Request,
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    if current_user is not None:
        return redirect_to("/dashboard")
    return render_template(
        request,
        "auth/forgot_password.html",
        settings=settings,
        current_user=None,
        errors={},
        success_message=None,
    )


@router.post("/forgot-password")
def forgot_password_action(
    request: Request,
    email: str = Form(...),
    settings: Settings = Depends(get_settings),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> Response:
    try:
        password_reset_service.request_password_reset(
            email=email,
            reset_link_base_url=str(request.base_url).rstrip("/"),
        )
    except OperationalError:
        return render_template(
            request,
            "auth/forgot_password.html",
            settings=settings,
            current_user=None,
            errors={"form": "Database is unavailable. Start PostgreSQL and try again."},
            success_message=None,
            values={"email": email},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return render_template(
        request,
        "auth/forgot_password.html",
        settings=settings,
        current_user=None,
        errors={},
        success_message="If the account exists, a password reset link has been sent.",
        values={"email": email},
    )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(
    request: Request,
    token: str = "",
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> Response:
    if current_user is not None:
        return redirect_to("/dashboard")

    token_valid = password_reset_service.validate_reset_token(token)
    return render_template(
        request,
        "auth/reset_password.html",
        settings=settings,
        current_user=None,
        token=token,
        token_valid=token_valid,
        errors={} if token_valid else {"form": "This reset link is invalid or has expired."},
    )


@router.post("/reset-password")
def reset_password_action(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    settings: Settings = Depends(get_settings),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> Response:
    try:
        if password != confirm_password:
            raise ValidationError("Passwords do not match.")
        password_reset_service.reset_password(raw_token=token, new_password=password)
    except (InvalidResetTokenError, ValidationError) as exc:
        return render_template(
            request,
            "auth/reset_password.html",
            settings=settings,
            current_user=None,
            token=token,
            token_valid=password_reset_service.validate_reset_token(token),
            errors={"form": str(exc)},
        )

    response = redirect_to("/login?reset=success")
    response.delete_cookie(settings.cookie_name)
    return response


@router.post("/register")
def register_action(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    try:
        user = auth_service.register_user(email=email, password=password, full_name=full_name)
    except (DuplicateEmailError, ValidationError) as exc:
        return render_template(
            request,
            "auth/register.html",
            settings=settings,
            current_user=None,
            errors={"form": str(exc)},
            values={"full_name": full_name, "email": email},
        )

    raw_token = auth_service.create_access_token(user_id=user.id)
    response = redirect_to("/dashboard")
    response.set_cookie(
        key=settings.cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )
    return response


@router.post("/logout")
def logout_action(
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    response = redirect_to("/login")
    response.delete_cookie(settings.cookie_name)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    if current_user is None:
        return redirect_to("/login")

    stats = [
        {"label": "Active projects", "value": "12"},
        {"label": "Seats in use", "value": "4"},
        {"label": "MRR tracked", "value": "$1,280"},
    ]
    return render_template(
        request,
        "dashboard/index.html",
        settings=settings,
        current_user=current_user,
        stats=stats,
    )


@router.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    if current_user is None:
        return redirect_to("/login")

    return render_template(
        request,
        "profile/index.html",
        settings=settings,
        current_user=current_user,
        errors={},
        success_message=None,
    )


@router.post("/profile")
def profile_action(
    request: Request,
    full_name: str = Form(...),
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> Response:
    if current_user is None:
        return redirect_to("/login")

    try:
        updated_user = profile_service.update_profile(current_user, full_name=full_name)
    except ValidationError as exc:
        return render_template(
            request,
            "profile/index.html",
            settings=settings,
            current_user=current_user,
            errors={"form": str(exc)},
            success_message=None,
        )

    return render_template(
        request,
        "profile/index.html",
        settings=settings,
        current_user=updated_user,
        errors={},
        success_message="Profile updated.",
    )


@router.get("/settings/billing", response_class=HTMLResponse)
def billing_page(
    request: Request,
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
    billing_service: BillingService = Depends(get_billing_service),
) -> Response:
    if current_user is None:
        return redirect_to("/login")

    billing_profile = billing_service.get_or_create_profile(current_user.id, current_user.email)
    return render_template(
        request,
        "settings/billing.html",
        settings=settings,
        current_user=current_user,
        billing_profile=billing_profile,
        errors={},
        success_message=None,
    )


@router.post("/settings/billing")
def billing_action(
    request: Request,
    company_name: str = Form(""),
    billing_email: str = Form(...),
    plan_name: str = Form("Starter"),
    tax_id: str = Form(""),
    settings: Settings = Depends(get_settings),
    current_user: User | None = Depends(get_optional_current_user),
    billing_service: BillingService = Depends(get_billing_service),
) -> Response:
    if current_user is None:
        return redirect_to("/login")

    try:
        billing_profile = billing_service.update_profile(
            user_id=current_user.id,
            company_name=company_name,
            billing_email=billing_email,
            plan_name=plan_name,
            tax_id=tax_id,
        )
    except ValidationError as exc:
        fallback_profile = billing_service.get_or_create_profile(current_user.id, current_user.email)
        return render_template(
            request,
            "settings/billing.html",
            settings=settings,
            current_user=current_user,
            billing_profile=fallback_profile,
            errors={"form": str(exc)},
            success_message=None,
        )

    return render_template(
        request,
        "settings/billing.html",
        settings=settings,
        current_user=current_user,
        billing_profile=billing_profile,
        errors={},
        success_message="Billing settings saved.",
    )
