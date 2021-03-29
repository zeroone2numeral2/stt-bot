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
    messages_to_delete = relationship("MessageToDelete", back_populates="chat", cascade="all, delete, delete-orphan, save-update")

    def __init__(self, chat_id):
        self.chat_id = chat_id

    def is_admin(self, user_id: int, permissions: [None, List], any_permission: bool = True, all_permissions: bool = False) -> bool:
        if any_permission == all_permissions:
            raise ValueError("only one between any_permission and all_permissions can be True or False")

        for chat_administrator in self.chat_administrators:
            if chat_administrator.user_id != user_id:
                continue

            if not permissions:
                return True

            for permission in permissions:
                if getattr(chat_administrator, permission):
                    if any_permission:
                        return True
                else:
                    return False

            if all_permissions:
                return True
            else:
                return False

        return False


Base.metadata.create_all(engine)
