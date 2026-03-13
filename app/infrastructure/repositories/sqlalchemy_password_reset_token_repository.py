from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.entities.password_reset_token import PasswordResetToken
from app.domain.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.infrastructure.database.models import PasswordResetTokenModel


def _to_entity(model: PasswordResetTokenModel) -> PasswordResetToken:
    return PasswordResetToken(
        id=str(model.id),
        user_id=str(model.user_id),
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        created_at=model.created_at,
        used_at=model.used_at,
    )


class SqlAlchemyPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def add(self, token: PasswordResetToken) -> PasswordResetToken:
        model = PasswordResetTokenModel(
            id=UUID(token.id),
            user_id=UUID(token.user_id),
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            created_at=token.created_at,
            used_at=token.used_at,
        )
        self.db_session.add(model)
        self.db_session.commit()
        self.db_session.refresh(model)
        return _to_entity(model)

    def get_active_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        model = (
            self.db_session.query(PasswordResetTokenModel)
            .filter(
                PasswordResetTokenModel.token_hash == token_hash,
                PasswordResetTokenModel.used_at.is_(None),
            )
            .one_or_none()
        )
        return _to_entity(model) if model is not None else None

    def mark_used(self, token_id: str) -> None:
        model = self.db_session.get(PasswordResetTokenModel, UUID(token_id))
        if model is None or model.used_at is not None:
            return
        model.used_at = _to_entity(model).mark_used().used_at
        self.db_session.commit()

    def mark_all_used_for_user(self, user_id: str) -> None:
        active_tokens = (
            self.db_session.query(PasswordResetTokenModel)
            .filter(
                PasswordResetTokenModel.user_id == UUID(user_id),
                PasswordResetTokenModel.used_at.is_(None),
            )
            .all()
        )
        for model in active_tokens:
            model.used_at = _to_entity(model).mark_used().used_at
        if active_tokens:
            self.db_session.commit()
