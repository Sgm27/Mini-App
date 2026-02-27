from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import base  # noqa: F401


def init_db(db: Session) -> None:
    """Placeholder for initial data seeding."""
    del db  # suppress unused variable warning for the template

