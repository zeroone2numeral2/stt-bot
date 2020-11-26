from sqlalchemy.orm import Session
from sqlalchemy import func

from bot.database.models.user import User


def superusers(session: Session):
    result = (
        session.query(User)
        .filter(User.superuser == True)
        .all()
    )

    return result
