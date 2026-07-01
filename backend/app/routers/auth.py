from fastapi import APIRouter, Depends, Request, status

from backend.app.core.dependencies import get_current_user
from backend.app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.schemas.response import SuccessResponse
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
_service = AuthService()


@router.post(
    "/register",
    response_model=SuccessResponse[AuthResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new account. Returns access and refresh tokens immediately.",
)
def register(req: RegisterRequest, request: Request) -> SuccessResponse[AuthResponse]:
    ip = request.client.host if request.client else None
    data = _service.register(req, ip)
    return SuccessResponse(message="Registration successful.", data=data)


@router.post(
    "/login",
    response_model=SuccessResponse[AuthResponse],
    summary="Login",
    description="Authenticate with email + password. Returns access and refresh tokens.",
)
def login(req: LoginRequest, request: Request) -> SuccessResponse[AuthResponse]:
    ip = request.client.host if request.client else None
    data = _service.login(req, ip)
    return SuccessResponse(message="Login successful.", data=data)


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new access token. "
        "Refresh tokens are single-use (rotated on every call)."
    ),
)
def refresh(req: RefreshRequest) -> SuccessResponse[TokenResponse]:
    tokens = _service.refresh(req)
    return SuccessResponse(message="Token refreshed.", data=tokens)


@router.post(
    "/logout",
    response_model=SuccessResponse[None],
    summary="Logout (revoke refresh token)",
)
def logout(
    req: RefreshRequest,
    current_user: UserResponse = Depends(get_current_user),
) -> SuccessResponse[None]:
    _service.logout(req.refresh_token, current_user.id)
    return SuccessResponse(message="Logged out successfully.")


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Get current user profile",
)
def me(current_user: UserResponse = Depends(get_current_user)) -> SuccessResponse[UserResponse]:
    return SuccessResponse(message="Profile fetched.", data=current_user)
