from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.models import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=str(model.id),
        email=model.email,
        full_name=model.full_name,
        password_hash=model.password_hash,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
        password_changed_at=model.password_changed_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def add(self, user: User) -> User:
        model = UserModel(
            id=UUID(user.id),
            email=user.email,
            full_name=user.full_name,
            password_hash=user.password_hash,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            password_changed_at=user.password_changed_at,
        )
        self.db_session.add(model)
        self.db_session.commit()
        self.db_session.refresh(model)
        return _to_entity(model)

    def get_by_email(self, email: str) -> User | None:
        model = self.db_session.query(UserModel).filter(UserModel.email == email).one_or_none()
        return _to_entity(model) if model is not None else None

    def get_by_id(self, user_id: str) -> User | None:
        model = self.db_session.get(UserModel, UUID(user_id))
        return _to_entity(model) if model is not None else None

    def update(self, user: User) -> User:
        model = self.db_session.get(UserModel, UUID(user.id))
        if model is None:
            raise ValueError("User not found.")

        model.full_name = user.full_name
        model.password_hash = user.password_hash
        model.is_active = user.is_active
        model.updated_at = user.updated_at
        model.password_changed_at = user.password_changed_at
        self.db_session.commit()
        self.db_session.refresh(model)
        return _to_entity(model)
