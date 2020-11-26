from sqlalchemy import Column, Integer, Boolean, String

from ..base import Base, engine


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    name = Column(String, default=None, nullable=True)  # this is just for superusers
    enabled = Column(Boolean, default=True)
    tos_accepted = Column(Boolean, default=False)
    superuser = Column(Boolean, default=False)

    def __init__(self, user_id):
        self.user_id = user_id

    def make_superuser(self, name: [str, None] = None):
        # self.tos_accepted = True
        self.superuser = True
        if name is not None:
            self.name = name

    def revoke_superuser(self):
        self.superuser = False
        self.name = None

    def revoke_tos(self, keep_name_if_superuser=True):
        self.tos_accepted = False
        if not self.superuser or (self.superuser and not keep_name_if_superuser):
            self.name = None


Base.metadata.create_all(engine)
