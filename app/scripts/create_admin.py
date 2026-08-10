import argparse
from getpass import getpass

from pydantic import ValidationError

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services.user_service import get_user_by_email


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or promote a Library API administrator.",
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    password = getpass("Admin password: ")
    password_confirmation = getpass("Confirm password: ")

    if password != password_confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        user_data = UserCreate(
            full_name=args.name,
            email=args.email,
            password=password,
        )
    except ValidationError as error:
        raise SystemExit(str(error)) from error

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_user = get_user_by_email(
            db,
            str(user_data.email),
        )

        if existing_user is not None:
            existing_user.full_name = user_data.full_name.strip()
            existing_user.hashed_password = get_password_hash(user_data.password)
            existing_user.role = UserRole.ADMIN
            existing_user.is_active = True
            db.commit()
            print(f"Existing user {existing_user.email} promoted to admin.")
            return

        admin = User(
            full_name=user_data.full_name.strip(),
            email=str(user_data.email).strip().lower(),
            hashed_password=get_password_hash(user_data.password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Admin {admin.email} created successfully.")


if __name__ == "__main__":
    main()
