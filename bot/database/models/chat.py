from sqlalchemy import Column, Integer, Boolean, String

from ..base import Base, engine


class Chat(Base):
    __tablename__ = 'chats'

    chat_id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=True)
    language = Column(String, default="it-IT")
    ignore_tos = Column(Boolean, default=False)
    ignore_if_shorter_than = Column(Integer, default=None)
    ignore_if_longer_than = Column(Integer, default=None)
    left = Column(Boolean, default=None)

    def __init__(self, chat_id):
        self.chat_id = chat_id


Base.metadata.create_all(engine)
