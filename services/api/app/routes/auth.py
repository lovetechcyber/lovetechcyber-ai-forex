
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.email import (
    email_is_configured,
    send_password_reset_email,
)
from app.core.security import (
    create_access_token,
    hash_password,
    password_hash,
    verify_password,
)
from app.db.mongo import get_database
from app.routes.auth_schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = f"{settings.api_v1_prefix}/auth"
RESET_TOKEN_TTL_MINUTES = 30

# Generated once per process to reduce timing differences for unknown emails.
DUMMY_PASSWORD_HASH = password_hash.hash(
    "dummy-password-never-used"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def public_user(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        role=user["role"],
        is_active=user["is_active"],
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    secure = settings.app_env == "production"

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="none" if secure else "strict",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    secure = settings.app_env == "production"

    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=secure,
        samesite="none" if secure else "strict",
        path=REFRESH_COOKIE_PATH,
    )


def require_trusted_origin(request: Request) -> None:
    origin = request.headers.get("origin")

    # Cookie-authenticated browser endpoints require an explicit trusted origin.
    if not origin or origin.rstrip("/") not in settings.allowed_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin not allowed",
        )


def create_refresh_record(
    user_id: ObjectId,
    family_id: str,
    token: str,
    token_version: int,
    now: datetime,
) -> dict:
    return {
        "user_id": user_id,
        "family_id": family_id,
        "token_hash": hash_token(token),
        "token_version": token_version,
        "created_at": now,
        "expires_at": now + timedelta(
            days=settings.refresh_token_expire_days
        ),
        "revoked_at": None,
        "replaced_by_hash": None,
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.login_rate_limit)
async def login(request: Request, body: LoginRequest, response: Response):
    email = str(body.email).strip().lower()
    password = body.password.get_secret_value()

    try:
        database = get_database()
        user = await database.users.find_one(
            {"email": email},
            {
                "email": 1,
                "password_hash": 1,
                "role": 1,
                "is_active": 1,
                "token_version": 1,
            },
        )
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from None

    stored_hash = (
        user.get("password_hash")
        if user and isinstance(user.get("password_hash"), str)
        else DUMMY_PASSWORD_HASH
    )

    password_valid = verify_password(password, stored_hash)

    if (
        user is None
        or not password_valid
        or user.get("is_active") is not True
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = utc_now()
    token_version = user.get("token_version", 0)
    if not isinstance(token_version, int) or isinstance(token_version, bool):
        token_version = 0

    refresh_token = make_refresh_token()
    family_id = str(uuid4())

    try:
        await database.refresh_tokens.insert_one(
            create_refresh_record(
                user_id=user["_id"],
                family_id=family_id,
                token=refresh_token,
                token_version=token_version,
                now=now,
            )
        )
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from None

    set_refresh_cookie(response, refresh_token)

    access_token = create_access_token(
        str(user["_id"]),
        token_version,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=public_user(user),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_session(request: Request, response: Response):
    require_trusted_origin(request)

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token or len(raw_token) > 256:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session is invalid or expired",
        )

    database = get_database()
    token_digest = hash_token(raw_token)
    now = utc_now()

    try:
        record = await database.refresh_tokens.find_one(
            {"token_hash": token_digest}
        )

        if record is None:
            clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session is invalid or expired",
            )

        # Reuse of a rotated token may indicate theft. Revoke its entire family.
        if record.get("revoked_at") is not None or record.get(
            "replaced_by_hash"
        ):
            await database.refresh_tokens.update_many(
                {"family_id": record["family_id"], "revoked_at": None},
                {"$set": {"revoked_at": now}},
            )
            clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session is invalid or expired",
            )

        if record["expires_at"] <= now:
            await database.refresh_tokens.update_one(
                {"_id": record["_id"], "revoked_at": None},
                {"$set": {"revoked_at": now}},
            )
            clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session is invalid or expired",
            )

        user = await database.users.find_one(
            {
                "_id": record["user_id"],
                "is_active": True,
            },
            {
                "email": 1,
                "role": 1,
                "is_active": 1,
                "token_version": 1,
            },
        )

        current_version = user.get("token_version", 0) if user else -1

        if (
            user is None
            or current_version != record.get("token_version", 0)
        ):
            await database.refresh_tokens.update_many(
                {"family_id": record["family_id"], "revoked_at": None},
                {"$set": {"revoked_at": now}},
            )
            clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session is invalid or expired",
            )

        new_token = make_refresh_token()
        new_digest = hash_token(new_token)

        # Atomic rotation: only one concurrent request can consume this token.
        rotated = await database.refresh_tokens.find_one_and_update(
            {
                "_id": record["_id"],
                "revoked_at": None,
                "replaced_by_hash": None,
                "expires_at": {"$gt": now},
            },
            {
                "$set": {
                    "revoked_at": now,
                    "replaced_by_hash": new_digest,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

        if rotated is None:
            await database.refresh_tokens.update_many(
                {"family_id": record["family_id"], "revoked_at": None},
                {"$set": {"revoked_at": now}},
            )
            clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session is invalid or expired",
            )

        await database.refresh_tokens.insert_one(
            create_refresh_record(
                user_id=user["_id"],
                family_id=record["family_id"],
                token=new_token,
                token_version=current_version,
                now=now,
            )
        )

    except HTTPException:
        raise
    except PyMongoError:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from None

    set_refresh_cookie(response, new_token)

    return TokenResponse(
        access_token=create_access_token(
            str(user["_id"]),
            current_version,
        ),
        expires_in=settings.access_token_expire_minutes * 60,
        user=public_user(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, response: Response):
    require_trusted_origin(request)

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    clear_refresh_cookie(response)

    if raw_token and len(raw_token) <= 256:
        try:
            database = get_database()
            record = await database.refresh_tokens.find_one(
                {"token_hash": hash_token(raw_token)}
            )

            if record:
                await database.refresh_tokens.update_many(
                    {
                        "family_id": record["family_id"],
                        "revoked_at": None,
                    },
                    {"$set": {"revoked_at": utc_now()}},
                )
        except PyMongoError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to complete logout. Please retry.",
            ) from None

    return MessageResponse(message="Logged out successfully")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(settings.password_reset_rate_limit)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
):
    generic_response = MessageResponse(
        message=(
            "If an eligible account exists, password reset instructions "
            "will be sent to its registered email address."
        )
    )

    # Do not create reset tokens when outbound email is not configured.
    if not email_is_configured():
        return generic_response

    email = str(body.email).strip().lower()

    try:
        database = get_database()
        user = await database.users.find_one(
            {"email": email, "is_active": True},
            {"_id": 1, "email": 1},
        )

        if user is None:
            return generic_response

        raw_token = secrets.token_urlsafe(32)
        token_digest = hash_token(raw_token)
        now = utc_now()

        await database.password_reset_tokens.delete_many(
            {
                "user_id": user["_id"],
                "used_at": None,
            }
        )

        await database.password_reset_tokens.insert_one(
            {
                "user_id": user["_id"],
                "token_hash": token_digest,
                "created_at": now,
                "expires_at": now + timedelta(
                    minutes=RESET_TOKEN_TTL_MINUTES
                ),
                "used_at": None,
            }
        )

        separator = "&" if "?" in settings.password_reset_url else "?"
        reset_url = (
            f"{settings.password_reset_url}{separator}"
            f"token={raw_token}"
        )

        try:
            await send_password_reset_email(user["email"], reset_url)
        except Exception:
            # Do not leave a valid token behind when email delivery fails.
            await database.password_reset_tokens.delete_one(
                {"token_hash": token_digest}
            )

        return generic_response

    except PyMongoError:
        # Keep account-existence information out of the response.
        return generic_response


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
):
    raw_token = body.token
    new_password = body.new_password.get_secret_value()

    if new_password.strip() != new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password cannot start or end with whitespace",
        )

    database = get_database()
    now = utc_now()
    token_digest = hash_token(raw_token)

    try:
        # Atomically consume the reset token: it cannot be used twice.
        reset_record = await database.password_reset_tokens.find_one_and_update(
            {
                "token_hash": token_digest,
                "used_at": None,
                "expires_at": {"$gt": now},
            },
            {"$set": {"used_at": now}},
            return_document=ReturnDocument.BEFORE,
        )

        if reset_record is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset link is invalid or expired",
            )

        user_id = reset_record["user_id"]

        updated_user = await database.users.update_one(
            {"_id": user_id, "is_active": True},
            {
                "$set": {"password_hash": hash_password(new_password)},
                "$inc": {"token_version": 1},
            },
        )

        if updated_user.modified_count != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset link is invalid or expired",
            )

        await database.refresh_tokens.update_many(
            {"user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )

        await database.password_reset_tokens.update_many(
            {"user_id": user_id, "used_at": None},
            {"$set": {"used_at": now}},
        )

    except HTTPException:
        raise
    except PyMongoError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset service temporarily unavailable",
        ) from None

    return MessageResponse(
        message="Password reset successful. Please sign in again."
    )


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)
