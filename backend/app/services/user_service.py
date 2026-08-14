import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


logger = logging.getLogger("library.users")


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    normalized_email = email.strip().lower()

    return db.scalar(select(User).where(User.email == normalized_email))


def create_user(
    db: Session,
    user_data: UserCreate,
) -> User:
    normalized_email = str(user_data.email).strip().lower()

    existing_user = get_user_by_email(
        db,
        normalized_email,
    )

    if existing_user:
        raise ValueError("A user with this email already exists.")

    user = User(
        full_name=user_data.full_name.strip(),
        email=normalized_email,
        hashed_password=get_password_hash(user_data.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(
        "user.created",
        extra={"user_id": user.id},
    )

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    user = get_user_by_email(db, email)

    if user is None:
        logger.warning("user.authentication_unknown_email")
        return None

    if not user.is_active:
        logger.warning(
            "user.authentication_inactive",
            extra={"user_id": user.id},
        )
        return None

    if not verify_password(password, user.hashed_password):
        logger.warning(
            "user.authentication_bad_password",
            extra={"user_id": user.id},
        )
        return None

    return user
