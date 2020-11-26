from sqlalchemy import Column, Integer, Boolean

from ..base import Base, engine


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=True)
    tos_accepted = Column(Boolean, default=False)
    superuser = Column(Boolean, default=False)

    def __init__(self, user_id):
        self.user_id = user_id

    def make_superuser(self):
        # self.tos_accepted = True
        self.superuser = True


Base.metadata.create_all(engine)
