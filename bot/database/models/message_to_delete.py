import datetime

from sqlalchemy import Column, Integer, Boolean, String, DateTime
from sqlalchemy.orm import relationship

from ..base import Base, engine


# class MessageToDelete(Base):
class MessageToDelete:
    __tablename__ = 'messages_to_delete'

    chat_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    sent_on = Column(DateTime, default=datetime.datetime.utcnow)
    delete_after = Column(Integer, nullable=True)  # in seconds
    can_delete = Column(Boolean, nullable=True)  # in case the bot doesn't have the permission

    def __init__(self, chat_id, message_id, delete_after: int = None):
        self.chat_id = chat_id
        self.message_id = message_id
        self.delete_after = delete_after


# Base.metadata.create_all(engine)
