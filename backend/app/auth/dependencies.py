import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.dependencies import get_db
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
)
logger = logging.getLogger("library.auth")


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        subject = payload.get("sub")

        if not isinstance(subject, str):
            raise credentials_exception()

        user_id = int(subject)

    except (InvalidTokenError, ValueError, TypeError) as error:
        logger.warning(
            "auth.token_validation_failed",
            extra={"reason": type(error).__name__},
        )
        raise credentials_exception() from error

    user = db.get(User, user_id)

    if user is None:
        logger.warning(
            "auth.token_user_missing",
            extra={"user_id": user_id},
        )
        raise credentials_exception()

    logger.debug(
        "auth.token_validated",
        extra={"user_id": user.id},
    )

    return user


def get_current_active_user(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
) -> User:
    if not current_user.is_active:
        logger.warning(
            "auth.inactive_user_blocked",
            extra={"user_id": current_user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )

    return current_user


def require_admin(
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
) -> User:
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "auth.admin_access_denied",
            extra={"user_id": current_user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )

    return current_user


def require_member(
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
) -> User:
    if current_user.role != UserRole.MEMBER:
        logger.warning(
            "auth.member_access_denied",
            extra={"user_id": current_user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member privileges required.",
        )

    return current_user
