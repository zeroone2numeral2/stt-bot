import datetime
from typing import List

from sqlalchemy import ForeignKey, Column, Integer, Boolean, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# noinspection PyPackageRequirements
from telegram import ChatMember

from ..base import Base, engine


def chat_members_to_dict(chat_id: int, chat_members: List[ChatMember]):
    result = {}
    for chat_member in chat_members:
        is_creator = chat_member.status == "creator"

        result[chat_member.user.id] = dict(
            chat_id=chat_id,
            user_id=chat_member.user.id,
            status=chat_member.status,
            is_anonymous=chat_member.is_anonymous,
            is_bot=chat_member.user.is_bot,
            can_manage_chat=chat_member.can_manage_chat if not is_creator else True,
            can_manage_voice_chats=chat_member.can_manage_voice_chats if not is_creator else True,
            can_change_info=chat_member.can_change_info if not is_creator else True,
            can_delete_messages=chat_member.can_delete_messages if not is_creator else True,
            can_invite_users=chat_member.can_invite_users if not is_creator else True,
            can_restrict_members=chat_member.can_restrict_members if not is_creator else True,
            can_pin_messages=chat_member.can_pin_messages if not is_creator else True,
            can_promote_members=chat_member.can_promote_members if not is_creator else True
        )

    return result


class ChatAdministrator(Base):
    __tablename__ = 'chat_administrators'

    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    chat_id = Column(Integer, ForeignKey('chats.chat_id', ondelete="CASCADE"), primary_key=True)
    status = Column(String)
    is_anonymous = Column(Boolean, default=False)
    is_bot = Column(Boolean, default=False)
    can_manage_chat = Column(Boolean, default=True)
    can_manage_voice_chats = Column(Boolean, default=False)
    can_change_info = Column(Boolean, default=False)
    can_delete_messages = Column(Boolean, default=False)
    can_invite_users = Column(Boolean, default=False)
    can_restrict_members = Column(Boolean, default=False)
    can_pin_messages = Column(Boolean, default=False)
    can_promote_members = Column(Boolean, default=False)
    # updated_on = Column(DateTime, default=datetime.datetime.utcnow)
    updated_on = Column(DateTime(timezone=True), onupdate=func.now())  # https://stackoverflow.com/a/33532154

    user = relationship("User", back_populates="chats_administrator")
    chat = relationship("Chat", back_populates="chat_administrators")

    def __old_init(self, chat_id, chat_member: ChatMember):
        self.chat_id = chat_id
        self.user_id = chat_member.user.id

        is_creator = chat_member.status == "creator"

        self.status = chat_member.status
        self.is_anonymous = chat_member.is_anonymous
        self.is_bot = chat_member.user.is_bot
        self.can_manage_chat = chat_member.can_manage_chat if not is_creator else True
        self.can_manage_voice_chats = chat_member.can_manage_voice_chats if not is_creator else True
        self.can_change_info = chat_member.can_change_info if not is_creator else True
        self.can_delete_messages = chat_member.can_delete_messages if not is_creator else True
        self.can_invite_users = chat_member.can_invite_users if not is_creator else True
        self.can_restrict_members = chat_member.can_restrict_members if not is_creator else True
        self.can_pin_messages = chat_member.can_pin_messages if not is_creator else True
        self.can_promote_members = chat_member.can_promote_members if not is_creator else True


Base.metadata.create_all(engine)
