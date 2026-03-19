from pydantic import BaseModel, EmailStr


class AuthRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
