from typing import List

from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base, engine


class Chat(Base):
    __tablename__ = 'chats'

    chat_id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=True)
    language = Column(String, default="it-IT")
    punctuation = Column(Boolean, default=None)
    ignore_if_shorter_than = Column(Integer, default=None)
    ignore_if_longer_than = Column(Integer, default=None)
    left = Column(Boolean, default=None)
    last_administrators_fetch = Column(DateTime(timezone=True), default=None, nullable=True)

    chat_administrators = relationship("ChatAdministrator", back_populates="chat", cascade="all, delete, delete-orphan, save-update")

    def __init__(self, chat_id):
        self.chat_id = chat_id


Base.metadata.create_all(engine)
