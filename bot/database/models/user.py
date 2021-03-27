from sqlalchemy import Column, Integer, Boolean, String
from sqlalchemy.orm import relationship

from ..base import Base, engine


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    name = Column(String, default=None, nullable=True)  # this is just for superusers
    enabled = Column(Boolean, default=True)
    opted_out = Column(Boolean, default=False)
    superuser = Column(Boolean, default=False)

    chats_administrator = relationship("ChatAdministrator", back_populates="user")

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

    def opt_out(self, keep_name_if_superuser=True):
        self.opted_out = True
        if not self.superuser or (self.superuser and not keep_name_if_superuser):
            self.name = None


Base.metadata.create_all(engine)
