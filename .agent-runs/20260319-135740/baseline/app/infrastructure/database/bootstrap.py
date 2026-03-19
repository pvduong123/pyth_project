from app.infrastructure.database.base import Base
from app.infrastructure.database import models  # noqa: F401
from app.infrastructure.database.session import engine


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
