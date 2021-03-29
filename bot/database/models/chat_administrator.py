import datetime
from typing import List

from sqlalchemy import ForeignKey, Column, Integer, Boolean, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# noinspection PyPackageRequirements
from telegram import ChatMember

from ..base import Base, engine


def chat_member_to_dict(chat_member: ChatMember) -> dict:
    is_creator = chat_member.status == "creator"

    return dict(
        user_id=chat_member.user.id,
        status=chat_member.status,
        is_anonymous=chat_member.is_anonymous,
        is_bot=chat_member.user.is_bot,
        can_manage_chat=chat_member.can_manage_chat or is_creator,
        can_manage_voice_chats=chat_member.can_manage_voice_chats or is_creator,
        can_change_info=chat_member.can_change_info or is_creator,
        can_delete_messages=chat_member.can_delete_messages or is_creator,
        can_invite_users=chat_member.can_invite_users or is_creator,
        can_restrict_members=chat_member.can_restrict_members or is_creator,
        can_pin_messages=chat_member.can_pin_messages or is_creator,
        can_promote_members=chat_member.can_promote_members or is_creator
    )


def chat_members_to_dict(chat_id: int, chat_members: List[ChatMember]):
    result = {}
    for chat_member in chat_members:
        result[chat_member.user.id] = chat_member_to_dict(chat_member).update({"chat_id": chat_id})

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

    @classmethod
    def from_chat_member(cls, chat_id, chat_member: ChatMember):
        chat_member_dict = chat_member_to_dict(chat_member).update({"chat_id": chat_id})

        return cls(**chat_member_dict)


Base.metadata.create_all(engine)
