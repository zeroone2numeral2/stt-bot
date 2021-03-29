import datetime
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import func
# noinspection PyPackageRequirements
from telegram import ChatMember

from bot.database.models.chat import Chat
from bot.database.models.chat_administrator import ChatAdministrator, chat_members_to_dict


def update_administrators(session: Session, chat: Chat, administrators: List[ChatMember]):
    current_chat_administrators_dict = chat_members_to_dict(chat.chat_id, administrators)

    chat_administrators = []
    for _, chat_member_dict in current_chat_administrators_dict.items():
        chat_administrator = ChatAdministrator(**chat_member_dict)
        chat_administrators.append(chat_administrator)

    # this also deletes the instances of ChatAdministrator currently not in 'current_chat_administrators_dict'
    chat.chat_administrators = chat_administrators
    chat.last_administrators_fetch = datetime.datetime.utcnow()


    session.add(chat)  # https://docs.sqlalchemy.org/en/13/orm/cascades.html#save-update
