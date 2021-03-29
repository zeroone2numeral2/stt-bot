import datetime

from sqlalchemy import ForeignKey, Column, Integer, Boolean, String, DateTime
from sqlalchemy.orm import relationship

from ..base import Base, engine


class MessageToDelete(Base):
    __tablename__ = 'messages_to_delete'

    chat_id = Column(Integer, ForeignKey('chats.chat_id', ondelete="CASCADE"), primary_key=True)
    message_id = Column(Integer, primary_key=True)
    sender_is_self = Column(Boolean, nullable=False)  # we need to know if the message was sent by us
    sent_on = Column(DateTime, default=datetime.datetime.utcnow)
    delete_after = Column(Integer, nullable=True)  # in seconds

    chat = relationship("Chat", back_populates="messages_to_delete")

    def __init__(self, chat_id, message_id, sender_is_self, delete_after: int = None):
        self.chat_id = chat_id
        self.message_id = message_id
        self.sender_is_self = sender_is_self
        self.delete_after = delete_after
