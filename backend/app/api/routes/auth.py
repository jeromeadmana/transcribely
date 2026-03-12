from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import secrets
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User, Organization, OrganizationMember, MemberRole
from app.schemas.user import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
)

# Temporary storage for OAuth auth codes (in production, use Redis)
_oauth_codes: dict[str, tuple[str, datetime]] = {}


class OAuthCodeExchange(BaseModel):
    code: str


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name,
    )
    db.add(user)

    # Create default organization for the user
    org_name = user_data.name or user_data.email.split("@")[0]
    organization = Organization(name=f"{org_name}'s Workspace")
    db.add(organization)
    await db.flush()

    # Add user as owner of the organization
    membership = OrganizationMember(
        user_id=user.id,
        organization_id=organization.id,
        role=MemberRole.OWNER,
    )
    db.add(membership)
    await db.commit()

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Generate new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user),
):
    """Get current authenticated user."""
    return UserResponse.model_validate(user)


# Google OAuth endpoints
@router.get("/google")
async def google_login():
    """Redirect to Google OAuth login page."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured",
        )

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.backend_url}/api/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback."""
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": f"{settings.backend_url}/api/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token",
            )

        tokens = token_response.json()

        # Get user info from Google
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info",
            )

        google_user = userinfo_response.json()

    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == google_user["email"])
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create new user
        user = User(
            email=google_user["email"],
            name=google_user.get("name"),
            avatar_url=google_user.get("picture"),
            password_hash=None,  # OAuth users don't have passwords
        )
        db.add(user)

        # Create default organization
        org_name = google_user.get("name") or google_user["email"].split("@")[0]
        organization = Organization(name=f"{org_name}'s Workspace")
        db.add(organization)
        await db.flush()

        # Add user as owner
        membership = OrganizationMember(
            user_id=user.id,
            organization_id=organization.id,
            role=MemberRole.OWNER,
        )
        db.add(membership)
        await db.commit()
    else:
        # Update avatar if changed
        if google_user.get("picture") and user.avatar_url != google_user.get("picture"):
            user.avatar_url = google_user.get("picture")
            await db.commit()

    # Generate a short-lived auth code instead of passing tokens in URL
    auth_code = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    _oauth_codes[auth_code] = (str(user.id), expires_at)

    # Clean up expired codes
    now = datetime.now(timezone.utc)
    expired_codes = [k for k, v in _oauth_codes.items() if v[1] < now]
    for code in expired_codes:
        del _oauth_codes[code]

    # Redirect to frontend with auth code (not tokens)
    redirect_url = f"{settings.frontend_url}/auth/callback?code={auth_code}"
    return RedirectResponse(url=redirect_url)


@router.post("/oauth/exchange", response_model=TokenResponse)
@limiter.limit("10/minute")
async def exchange_oauth_code(
    request: Request,
    code_request: OAuthCodeExchange,
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth auth code for tokens."""
    code_data = _oauth_codes.get(code_request.code)

    if not code_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired auth code",
        )

    user_id, expires_at = code_data

    if datetime.now(timezone.utc) > expires_at:
        del _oauth_codes[code_request.code]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auth code expired",
        )

    # Remove used code
    del _oauth_codes[code_request.code]

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )
