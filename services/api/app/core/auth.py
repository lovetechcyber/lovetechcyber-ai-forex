
import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pymongo.errors import PyMongoError

from app.core.security import decode_access_token
from app.db.mongo import get_database


bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        token_version = payload.get("ver")

        if payload.get("type") != "access":
            raise unauthorized()

        if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):
            raise unauthorized()

        if (
            isinstance(token_version, bool)
            or not isinstance(token_version, int)
            or token_version < 0
        ):
            raise unauthorized()

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized() from None

    try:
        database = get_database()
        user = await database.users.find_one(
            {"_id": ObjectId(user_id)},
            {
                "email": 1,
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

    if user is None or user.get("is_active") is not True:
        raise unauthorized()

    current_version = user.get("token_version", 0)

    if (
        isinstance(current_version, bool)
        or not isinstance(current_version, int)
        or token_version != current_version
    ):
        raise unauthorized()

    return user
