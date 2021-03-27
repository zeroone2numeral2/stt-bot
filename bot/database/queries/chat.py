from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import func
# noinspection PyPackageRequirements
from telegram import ChatMember

from bot.database.models.chat import Chat
from bot.database.models.chat_administrator import ChatAdministrator


def save_chat_administrators(session: Session, chat: Chat, administrators: List[ChatMember]):
    chat_administrators = []
    for chat_member in administrators:
        chat_administrator = ChatAdministrator(chat.chat_id, chat_member)
        chat_administrators.append(chat_administrator)

    chat.chat_administrators = chat_administrators
    chat.last_administrators_fetch = func.now()

    session.add(chat)  # https://docs.sqlalchemy.org/en/13/orm/cascades.html#save-update
