import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import ChatMemberHandler, Filters, CallbackContext
# noinspection PyPackageRequirements
from telegram import Update, ChatMember

from bot import sttbot
from bot.bot import AdminPermission
from bot.database.models.chat import Chat
from bot.database.models.chat_administrator import ChatAdministrator, chat_member_to_dict
from bot.database.queries import chat as chat_queries
from bot.decorators import decorators
from config import config

logger = logging.getLogger(__name__)


@decorators.catchexceptions()
@decorators.pass_session(pass_chat=True)
@decorators.administrator(skip_refresh=True)
def on_chat_member_update(update: Update, _, session: Session, chat: Chat):
    logger.info("chat member update")

    new_chat_member: ChatMember = update.chat_member.new_chat_member if update.chat_member else update.my_chat_member.new_chat_member
    old_chat_member: ChatMember = update.chat_member.old_chat_member if update.chat_member else update.my_chat_member.old_chat_member
    user_id = new_chat_member.user.id

    if old_chat_member.status in ("administrator", "creator") and new_chat_member.status in ("member", "kicked"):
        chat_administrator = chat.get_administrator(user_id)
        if chat_administrator:
            session.delete(chat_administrator)
            logger.info("chat member: deleted db record")
        else:
            logger.info("no record to delete")
    elif new_chat_member.status in ("administrator", "creator"):
        new_chat_member_dict = chat_member_to_dict(new_chat_member, update.effective_chat.id)
        chat_administrator = ChatAdministrator(**new_chat_member_dict)
        session.merge(chat_administrator)
        logger.info("chat member: updated/inserted db record")


sttbot.add_handler(ChatMemberHandler(on_chat_member_update, ChatMemberHandler.ANY_CHAT_MEMBER))
