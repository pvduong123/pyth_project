from app.application.errors import ValidationError
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository


class ProfileService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def update_profile(self, user: User, full_name: str) -> User:
        cleaned_name = full_name.strip()
        if not cleaned_name:
            raise ValidationError("Full name is required.")

        updated_user = user.with_updates(full_name=cleaned_name)
        return self.user_repository.update(updated_user)
