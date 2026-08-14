import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.core.security import create_access_token
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import authenticate_user, create_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)
logger = logging.getLogger("library.auth")


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    try:
        user = create_user(db, user_data)
        logger.info(
            "auth.registration_succeeded",
            extra={"user_id": user.id},
        )
        return user

    except ValueError as error:
        logger.warning(
            "auth.registration_failed",
            extra={"reason": str(error)},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.post(
    "/login",
    response_model=Token,
)
def login(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    logger.info("auth.login_attempt")
    user = authenticate_user(
        db,
        form_data.username,
        form_data.password,
    )

    if user is None:
        logger.warning("auth.login_failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id),
    )

    logger.info(
        "auth.login_succeeded",
        extra={"user_id": user.id},
    )

    return Token(access_token=access_token)


@router.get(
    "/me",
    response_model=UserRead,
)
def read_current_user(
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
) -> User:
    return current_user
